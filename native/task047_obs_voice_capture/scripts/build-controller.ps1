param(
  [string]$Compiler = 'C:\Program Files\Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe'
)

$ErrorActionPreference = 'Stop'
$pluginRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$source = Join-Path $pluginRoot 'controller\BaiVoiceCaptureController.cs'
$buildRoot = Join-Path $pluginRoot 'controller\build'
$output = Join-Path $buildRoot 'bai-voice-capture-controller.exe'
if (!(Test-Path -LiteralPath $Compiler)) { throw "Pinned C# compiler not found: $Compiler" }
if (!(Test-Path -LiteralPath $source)) { throw 'Controller source not found' }
New-Item -ItemType Directory -Path $buildRoot -Force | Out-Null

& $Compiler /nologo /warnaserror+ /target:winexe /platform:x64 /optimize+ `
  "/out:$output" /reference:System.dll /reference:System.Core.dll `
  /reference:System.Drawing.dll /reference:System.Windows.Forms.dll $source
if ($LASTEXITCODE -ne 0) { throw "Controller build failed with exit code $LASTEXITCODE" }

$test = Start-Process -FilePath $output -ArgumentList '--self-test' -Wait -PassThru
if ($test.ExitCode -ne 0) { throw "Controller self-test failed with exit code $($test.ExitCode)" }
Write-Output "CONTROLLER_BUILD_TEST_PASS exe=$output"
