<#
  Instala a stack AEC para Claude Code no Windows 10/11.

  Uso (PowerShell, na pasta do repositório):
    Set-ExecutionPolicy -Scope Process Bypass
    .\setup\instalar-windows.ps1                 # stack aberta (recomendada)
    .\setup\instalar-windows.ps1 -SketchUp -Rhino -Archicad -Bonsai -PluginArquitetura -SkillsDDC

  O que instala:
    Programas (winget): Git, Python 3.12, uv, Node.js LTS, Blender, FreeCAD, LibreCAD
    Bibliotecas Python em %USERPROFILE%\aec-stack\.venv (setup\requirements.txt)
    MCPs no Claude Code (escopo do usuário): blender, freecad, autocad (ezdxf/AutoCAD)
    Skills deste repositório em %USERPROFILE%\.claude\skills
  Opcionais: MCPs de SketchUp, Rhino, Archicad e Bonsai; plugin de arquitetura (AlpacaLabs); skills DDC.

  Programas comerciais (Revit, SketchUp, Rhino, Archicad, AutoCAD) NÃO são instalados: precisam de licença.
#>
param(
  [switch]$SketchUp, [switch]$Rhino, [switch]$Archicad, [switch]$Bonsai,
  [switch]$PluginArquitetura, [switch]$SkillsDDC, [switch]$SemProgramas
)
$ErrorActionPreference = "Continue"
$Repo  = Split-Path -Parent $PSScriptRoot
$Stack = Join-Path $env:USERPROFILE "aec-stack"
$Pendencias = New-Object System.Collections.Generic.List[string]

function Passo($t) { Write-Host "`n==> $t" -ForegroundColor Cyan }
function Ok($t)    { Write-Host "    [ok] $t" -ForegroundColor Green }
function Aviso($t) { Write-Host "    [!]  $t" -ForegroundColor Yellow; $Pendencias.Add($t) }
function Atualizar-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
              [Environment]::GetEnvironmentVariable("Path", "User") + ";" +
              (Join-Path $env:USERPROFILE ".local\bin")
}
function Instalar-Winget($id) {
  $lista = winget list --id $id -e --accept-source-agreements 2>$null | Out-String
  if ($lista -match [regex]::Escape($id)) { Ok "$id já instalado"; return }
  winget install --id $id -e --silent --accept-source-agreements --accept-package-agreements
  if ($LASTEXITCODE -eq 0) { Ok "$id instalado" } else { Aviso "winget falhou para $id (código $LASTEXITCODE)" }
}
function Mcp-Add($nome, [string[]]$cmd, [string[]]$envs = @()) {
  claude mcp remove $nome -s user 2>$null | Out-Null
  $a = @("mcp", "add", $nome, "-s", "user")
  foreach ($e in $envs) { $a += @("-e", $e) }
  $a += "--"; $a += $cmd
  & claude @a
  if ($LASTEXITCODE -eq 0) { Ok "MCP '$nome' registrado" } else { Aviso "falha ao registrar MCP '$nome'" }
}

# 1. Programas -------------------------------------------------------------
if (-not $SemProgramas) {
  Passo "Programas (winget)"
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Aviso "winget não encontrado. Instale o 'App Installer' pela Microsoft Store e rode de novo."
  } else {
    foreach ($id in @("Git.Git", "Python.Python.3.12", "astral-sh.uv", "OpenJS.NodeJS.LTS",
                      "BlenderFoundation.Blender", "FreeCAD.FreeCAD", "LibreCAD.LibreCAD")) {
      Instalar-Winget $id
    }
  }
}
Atualizar-Path
foreach ($c in @("git", "uv", "uvx")) {
  if (-not (Get-Command $c -ErrorAction SilentlyContinue)) {
    Write-Host "`n'$c' não está no PATH. Feche e abra o PowerShell e rode o script de novo." -ForegroundColor Red
    exit 1
  }
}
$TemClaude = [bool](Get-Command claude -ErrorAction SilentlyContinue)
if (-not $TemClaude) { Aviso "Claude Code não encontrado no PATH: MCPs e plugins não serão registrados" }

# 2. Bibliotecas Python ----------------------------------------------------
Passo "Bibliotecas Python em $Stack\.venv"
New-Item -ItemType Directory -Force -Path $Stack | Out-Null
$Py = Join-Path $Stack ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { uv venv --python 3.12 (Join-Path $Stack ".venv") }
uv pip install --python $Py -r (Join-Path $PSScriptRoot "requirements.txt")
if ($LASTEXITCODE -eq 0) { Ok "bibliotecas instaladas" } else { Aviso "falha no pip install (veja acima)" }

# 3. Repositórios dos MCPs -------------------------------------------------
function Clonar($url, $dir) {
  if (Test-Path (Join-Path $dir ".git")) { git -C $dir pull --ff-only | Out-Null }
  else { git clone --depth 1 $url $dir }
}
Passo "AutoCAD/DXF MCP (puran-water/autocad-mcp)"
$Acad = Join-Path $Stack "autocad-mcp"
Clonar "https://github.com/puran-water/autocad-mcp.git" $Acad
Push-Location $Acad; uv sync; $r = $LASTEXITCODE; Pop-Location
if ($r -eq 0) { Ok "autocad-mcp pronto (backend auto: AutoCAD aberto → File IPC; senão ezdxf)" } else { Aviso "uv sync falhou em autocad-mcp" }

Passo "FreeCAD MCP: addon"
$Fc = Join-Path $Stack "freecad-mcp"
Clonar "https://github.com/neka-nat/freecad-mcp.git" $Fc
$ModDir = $null
$FcCmd = Get-ChildItem "C:\Program Files\FreeCAD*\bin\FreeCADCmd.exe", "$env:LOCALAPPDATA\Programs\FreeCAD*\bin\FreeCADCmd.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($FcCmd) {
  $saida = & $FcCmd.FullName -c "import FreeCAD,os;print('MODDIR='+os.path.join(FreeCAD.getUserAppDataDir(),'Mod'))" 2>$null | Out-String
  if ($saida -match "MODDIR=(.+)") { $ModDir = $Matches[1].Trim() }
}
if (-not $ModDir) { $ModDir = Join-Path $env:APPDATA "FreeCAD\v1-1\Mod"; Aviso "pasta Mod do FreeCAD presumida: $ModDir (confira)" }
New-Item -ItemType Directory -Force -Path $ModDir | Out-Null
Copy-Item -Recurse -Force (Join-Path $Fc "addon\FreeCADMCP") $ModDir
Ok "addon copiado para $ModDir\FreeCADMCP"

Passo "Blender MCP: addon"
uvx mcp-for-blender install-addon
if ($LASTEXITCODE -eq 0) { Ok "addon do Blender instalado" } else { Aviso "rode 'uvx mcp-for-blender install-addon' com o Blender fechado" }

if ($Bonsai) {
  Passo "Bonsai MCP (IFC no Blender)"
  Clonar "https://github.com/JotaDeRodriguez/Bonsai_mcp.git" (Join-Path $Stack "Bonsai_mcp")
  Aviso "Bonsai MCP: instale o addon.py do Bonsai_mcp no Blender (ele substitui o addon do Blender MCP; use um dos dois por vez)"
}

# 4. Registrar MCPs no Claude Code -----------------------------------------
if ($TemClaude) {
  Passo "Registrando servidores MCP no Claude Code (escopo do usuário)"
  Mcp-Add "blender" @("uvx", "mcp-for-blender")
  Mcp-Add "freecad" @("uvx", "freecad-mcp")
  Mcp-Add "autocad" @((Join-Path $Acad ".venv\Scripts\python.exe"), "-m", "autocad_mcp") @("AUTOCAD_MCP_BACKEND=auto")
  if ($SketchUp) { Mcp-Add "sketchup" @("uvx", "sketchup-mcp2"); Aviso "SketchUp: instale o .rbz de github.com/zinin/sketchup-mcp2/releases (Window > Extension Manager)" }
  if ($Rhino)    { Mcp-Add "rhino" @("uvx", "rhinomcp@latest"); Aviso "Rhino 8.20+: Tools > Package Manager > 'rhinomcp' > Install; depois rode o comando mcpstart" }
  if ($Archicad) { Mcp-Add "archicad" @("uvx", "--from", "tapir-archicad-mcp", "archicad-server"); Aviso "Archicad: instale o add-on Tapir (github.com/ENZYME-APD/tapir-archicad-automation)" }
  if ($Bonsai)   { Mcp-Add "bonsai" @("uv", "--directory", (Join-Path $Stack "Bonsai_mcp"), "run", "tools.py") }
}

# 5. Skills e plugins ------------------------------------------------------
Passo "Skills deste repositório → $env:USERPROFILE\.claude\skills"
$Dest = Join-Path $env:USERPROFILE ".claude\skills"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Get-ChildItem (Join-Path $Repo ".claude\skills") -Directory | ForEach-Object {
  Copy-Item -Recurse -Force $_.FullName $Dest; Ok "skill $($_.Name)"
}
if ($PluginArquitetura -and $TemClaude) {
  Passo "Plugin Arch Studio (AlpacaLabsLLC/skills-for-architects)"
  claude plugin marketplace add AlpacaLabsLLC/skills-for-architects
  claude plugin install as@skills-for-architects
  Aviso "Arch Studio envia um ping anônimo diário de versão/uso; veja o README do projeto para desligar"
}
if ($SkillsDDC) {
  Passo "Skills DDC de orçamento (datadrivenconstruction)"
  npx --yes skills add datadrivenconstruction/ddc_skills_for_ai_agents_in_construction --skill estimate-builder --agent claude-code
}

# 6. Verificação e próximos passos -----------------------------------------
Passo "Verificação"
& $Py (Join-Path $PSScriptRoot "verificar_stack.py")

Write-Host "`n==> Passos manuais" -ForegroundColor Cyan
Write-Host @"
  1. Blender: Edit > Preferences > Get Extensions > busque 'Bonsai' > Install (BIM/IFC).
     Para o MCP: tecla N na viewport 3D > aba 'MCP for Blender' > Start MCP Server.
  2. FreeCAD: abra a bancada 'MCP Addon' > Start RPC Server.
  3. DWG: baixe o ODA File Converter (opendesign.com/guestfiles/oda_file_converter) para converter DXF <-> DWG.
  4. SINAPI: baixe a planilha do mês/UF em caixa.gov.br/sinapi para usar a skill orcamento-sinapi.
  5. Reinicie o Claude Code e rode /mcp para ver os servidores.
  Python da stack: $Py
"@
if ($Pendencias.Count) {
  Write-Host "`n==> Pendências" -ForegroundColor Yellow
  $Pendencias | ForEach-Object { Write-Host "  - $_" }
}
