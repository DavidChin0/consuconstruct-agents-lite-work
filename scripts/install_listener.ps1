# install_listener.ps1 — deja inbox_listener.py vivo en Windows (tarea programada al iniciar sesion).
# Uso:  powershell -ExecutionPolicy Bypass -File scripts\install_listener.ps1 -Url http://100.x.x.x:24425/sse -Role claude_dane
# El token NO se guarda en la tarea: se lee de la variable de usuario MCP_LITE_TOKEN
# (definila una vez:  setx MCP_LITE_TOKEN "<tu token>").
param(
    [Parameter(Mandatory)] [string]$Url,
    [Parameter(Mandatory)] [ValidateSet('claude_dane','codex_hector','claude_reviewer','devops_bot','reviewer')] [string]$Role,
    [string]$Python = 'python'
)
$repo = Split-Path -Parent $PSScriptRoot
$script = Join-Path $repo 'scripts\inbox_listener.py'
[Environment]::SetEnvironmentVariable('MCP_LITE_URL', $Url, 'User')
[Environment]::SetEnvironmentVariable('MCP_LITE_ROLE', $Role, 'User')
if (-not [Environment]::GetEnvironmentVariable('MCP_LITE_TOKEN', 'User')) {
    Write-Warning 'Falta MCP_LITE_TOKEN (variable de usuario). Definila antes de iniciar la tarea.'
}
$action = New-ScheduledTaskAction -Execute $Python -Argument "`"$script`"" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable
Register-ScheduledTask -TaskName 'ConsuLiteInboxListener' -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Host 'Tarea ConsuLiteInboxListener registrada. Iniciar ahora: Start-ScheduledTask ConsuLiteInboxListener'
