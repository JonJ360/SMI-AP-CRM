param([switch]$Install,[switch]$RefreshGuard)
$ErrorActionPreference='Stop'
$repo='C:\Users\jonj\OneDrive\360\360 Solutions\Clients\360 Solutions LLC\A.I\GitHub\SMI-AP-CRM'
$private='C:\Users\jonj\AppData\Local\hermes\ap-crm'
$python='C:\Users\jonj\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe'
$name='Hermes_APCRM_GP_Refresh'
if($Install -or $RefreshGuard){
 if($Install -and (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue)){throw 'Task already exists; review before replacement'}
 $files=@{}
 @("$repo\ap_refresh.py","$repo\scheduled_refresh.py","$repo\gp_extract.py","$repo\check_runs.py","$repo\ap.py","$repo\..\financial-statements\scripts\financial_sync.py","$repo\..\SMI-AR-CRM\scripts\arcrm_ledger_auth.py") | ForEach-Object {$p=(Resolve-Path $_).Path;$files[$p]=(Get-FileHash $p -Algorithm SHA256).Hash.ToLower()}
 @{entrypoint="$repo\ap_refresh.py";files=$files} | ConvertTo-Json -Depth 5 | Set-Content -Encoding ASCII "$private\deployment.json"
}
if($Install){
 $action=New-ScheduledTaskAction -Execute $python -Argument ('"'+$repo+'\scheduled_refresh.py"') -WorkingDirectory $repo
 $trigger=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
 $principal=New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
 $settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 4) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
 Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'AP-only deterministic SELECT-only SMI/SFAB refresh, reconciliation, atomic owner-only publish, verified readback. Requires Jon logged in and GP LAN. No LLM/payment execution.' | Out-Null
}
$t=Get-ScheduledTask -TaskName $name;$i=$t | Get-ScheduledTaskInfo
$r=@{Name=$t.TaskName;State=[string]$t.State;User=$t.Principal.UserId;LogonType=[string]$t.Principal.LogonType;RunLevel=[string]$t.Principal.RunLevel;Actions=$t.Actions | Select-Object Execute,Arguments,WorkingDirectory;Triggers=$t.Triggers | Select-Object StartBoundary,@{n='Interval';e={$_.Repetition.Interval}};MultipleInstances=[string]$t.Settings.MultipleInstances;ExecutionTimeLimit=$t.Settings.ExecutionTimeLimit;LastRun=$i.LastRunTime.ToString('o');LastResult=$i.LastTaskResult;NextRun=$i.NextRunTime.ToString('o')}
$r | ConvertTo-Json -Depth 6 | Set-Content -Encoding ASCII 'C:\Users\jonj\OneDrive\Hermes\Documents\AP-Publication-Evidence\refresh-task.json'
$r | ConvertTo-Json -Depth 6
