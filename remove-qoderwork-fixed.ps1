#Requires -Version 5.1
#Requires -RunAsAdministrator

param(
    [switch]$Preview
)

$ErrorActionPreference = "SilentlyContinue"
$Pattern = "qoder[\s_-]*work|qoderwork|\.qoderwork"

function Test-QoderText {
    param([string[]]$Text)
    return (($Text -join " ") -match $Pattern)
}

function Remove-ExactFolder {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return
    }
    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    if ($Preview) {
        Write-Host "[Preview] Remove folder: $Path" -ForegroundColor Yellow
    }
    else {
        Remove-Item -LiteralPath $Path -Recurse -Force
        Write-Host "Removed folder: $Path" -ForegroundColor Green
    }
}

Write-Host "QoderWork cleanup started." -ForegroundColor Cyan

# Remove scheduled tasks first so that they cannot restart the process.
$tasks = Get-ScheduledTask
foreach ($task in $tasks) {
    $actionText = ""
    foreach ($action in $task.Actions) {
        $actionText += " $($action.Execute) $($action.Arguments) $($action.WorkingDirectory)"
    }

    $matched = Test-QoderText -Text @(
        $task.TaskName,
        $task.TaskPath,
        $actionText
    )

    if ($matched) {
        $fullTaskName = "$($task.TaskPath)$($task.TaskName)"
        if ($Preview) {
            Write-Host "[Preview] Remove task: $fullTaskName" -ForegroundColor Yellow
        }
        else {
            Disable-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath | Out-Null
            Unregister-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath -Confirm:$false
            Write-Host "Removed task: $fullTaskName" -ForegroundColor Green
        }
    }
}

# Stop and delete QoderWork services.
$services = Get-CimInstance Win32_Service
foreach ($service in $services) {
    $matched = Test-QoderText -Text @(
        $service.Name,
        $service.DisplayName,
        $service.PathName
    )

    if ($matched) {
        if ($Preview) {
            Write-Host "[Preview] Remove service: $($service.Name)" -ForegroundColor Yellow
        }
        else {
            Stop-Service -Name $service.Name -Force
            Start-Sleep -Milliseconds 500
            sc.exe delete $service.Name | Out-Null
            Write-Host "Removed service: $($service.Name)" -ForegroundColor Green
        }
    }
}

# Find QoderWork processes by name, path, or command line.
$allProcesses = Get-CimInstance Win32_Process
$qoderProcessIds = @()
foreach ($process in $allProcesses) {
    $matched = Test-QoderText -Text @(
        $process.Name,
        $process.ExecutablePath,
        $process.CommandLine
    )
    if ($matched) {
        $qoderProcessIds += [int]$process.ProcessId
    }
}

# Check port 19830, but do not kill an unrelated process.
$listeners = @(Get-NetTCPConnection -LocalPort 19830 -State Listen)
foreach ($listener in $listeners) {
    $ownerPid = [int]$listener.OwningProcess
    $owner = $allProcesses | Where-Object { $_.ProcessId -eq $ownerPid }

    if ($ownerPid -eq 4) {
        Write-Warning "Port 19830 is owned by PID 4. It was not stopped."
        continue
    }

    $matched = Test-QoderText -Text @(
        $owner.Name,
        $owner.ExecutablePath,
        $owner.CommandLine
    )

    if ($matched) {
        $qoderProcessIds += $ownerPid
    }
    else {
        Write-Warning "Port 19830 is owned by a non-QoderWork process. It was not stopped."
        $owner | Format-List ProcessId, Name, ExecutablePath, CommandLine
    }
}

$qoderProcessIds = $qoderProcessIds | Sort-Object -Unique
foreach ($processId in $qoderProcessIds) {
    if ($Preview) {
        Write-Host "[Preview] Stop process PID: $processId" -ForegroundColor Yellow
    }
    else {
        Stop-Process -Id $processId -Force
        Write-Host "Stopped process PID: $processId" -ForegroundColor Green
    }
}

# Remove QoderWork startup registry values.
$runKeys = @(
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"
)

foreach ($runKey in $runKeys) {
    if (-not (Test-Path -LiteralPath $runKey)) {
        continue
    }

    $properties = (Get-ItemProperty -LiteralPath $runKey).PSObject.Properties
    foreach ($property in $properties) {
        if ($property.Name -match "^PS") {
            continue
        }

        $matched = Test-QoderText -Text @(
            $property.Name,
            [string]$property.Value
        )

        if ($matched) {
            if ($Preview) {
                Write-Host "[Preview] Remove startup value: $runKey -> $($property.Name)" -ForegroundColor Yellow
            }
            else {
                Remove-ItemProperty -LiteralPath $runKey -Name $property.Name -Force
                Write-Host "Removed startup value: $($property.Name)" -ForegroundColor Green
            }
        }
    }
}

# Remove only known, exact QoderWork folders.
$folders = @(
    "$env:USERPROFILE\.qoderwork",
    "$env:USERPROFILE\.qoderworkcn",
    "$env:LOCALAPPDATA\QoderWork",
    "$env:LOCALAPPDATA\QoderWorkCN",
    "$env:LOCALAPPDATA\Programs\QoderWork",
    "$env:LOCALAPPDATA\Programs\QoderWork CN",
    "$env:APPDATA\QoderWork",
    "$env:APPDATA\QoderWorkCN",
    "$env:ProgramFiles\QoderWork",
    "$env:ProgramFiles\QoderWork CN"
)

$programFilesX86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
if (-not [string]::IsNullOrWhiteSpace($programFilesX86)) {
    $folders += "$programFilesX86\QoderWork"
    $folders += "$programFilesX86\QoderWork CN"
}

foreach ($folder in ($folders | Sort-Object -Unique)) {
    Remove-ExactFolder -Path $folder
}

$remaining = @(Get-NetTCPConnection -LocalPort 19830 -State Listen)
if ($remaining.Count -eq 0) {
    Write-Host "Completed. Port 19830 is free." -ForegroundColor Green
}
else {
    Write-Warning "Port 19830 is still in use:"
    $remaining | Format-Table LocalAddress, LocalPort, OwningProcess
}

if ($Preview) {
    Write-Host "Preview completed. No changes were made." -ForegroundColor Yellow
}
else {
    Write-Host "Restart Windows after cleanup." -ForegroundColor Cyan
}
