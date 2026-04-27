. "$PSScriptRoot\common.ps1"

Assert-Administrator

$envValues = Read-DotEnv
$vmName = $envValues.WINDOWS_VM_NAME
$vmPath = $envValues.WINDOWS_VM_PATH
$isoPath = Resolve-TestEnvPath $envValues.ROCKY_ISO_PATH
$switchName = $envValues.HYPERV_SWITCH_NAME
$externalAdapterName = $envValues.HYPERV_EXTERNAL_NET_ADAPTER_NAME
$memoryStartupBytes = [int64]$envValues.VM_MEMORY_STARTUP_BYTES
$processorCount = [int]$envValues.VM_PROCESSOR_COUNT
$vhdSizeBytes = [int64]$envValues.VM_VHD_SIZE_BYTES

if (-not (Get-Command Get-VM -ErrorAction SilentlyContinue)) {
    throw "Hyper-V PowerShell module is not available. Enable Hyper-V first."
}

if (-not (Test-Path $isoPath)) {
    throw "Rocky Linux ISO not found: $isoPath"
}

if (-not (Get-VMSwitch -Name $switchName -ErrorAction SilentlyContinue)) {
    if ([string]::IsNullOrWhiteSpace($externalAdapterName)) {
        $availableAdapters = Get-NetAdapter -Physical -ErrorAction SilentlyContinue |
            Where-Object { $_.Status -eq "Up" } |
            Select-Object -ExpandProperty Name
        $adapterList = if ($availableAdapters) { $availableAdapters -join ", " } else { "No active physical adapters found" }
        throw "Hyper-V switch '$switchName' does not exist. Windows Server usually has no Default Switch. Set HYPERV_SWITCH_NAME to an existing switch, or set HYPERV_EXTERNAL_NET_ADAPTER_NAME in .env to create an external switch. Active adapters: $adapterList"
    }
    New-VMSwitch -Name $switchName -NetAdapterName $externalAdapterName -AllowManagementOS $true
}

if (Get-VM -Name $vmName -ErrorAction SilentlyContinue) {
    Write-Host "VM already exists: $vmName"
    return
}

New-Item -ItemType Directory -Force -Path $vmPath | Out-Null
$vhdPath = Join-Path $vmPath "$vmName\Virtual Hard Disks\$vmName.vhdx"

New-VM -Name $vmName `
    -Generation 2 `
    -MemoryStartupBytes $memoryStartupBytes `
    -SwitchName $switchName `
    -Path $vmPath `
    -NewVHDPath $vhdPath `
    -NewVHDSizeBytes $vhdSizeBytes

Set-VMProcessor -VMName $vmName -Count $processorCount
Set-VMMemory -VMName $vmName -DynamicMemoryEnabled $true -MinimumBytes 2147483648 -StartupBytes $memoryStartupBytes -MaximumBytes 4294967296
Set-VMFirmware -VMName $vmName -EnableSecureBoot On -SecureBootTemplate MicrosoftUEFICertificateAuthority
Add-VMDvdDrive -VMName $vmName -Path $isoPath
$dvd = Get-VMDvdDrive -VMName $vmName
Set-VMFirmware -VMName $vmName -FirstBootDevice $dvd

Write-Host "VM created: $vmName"
Write-Host "Start the VM and install Rocky Linux 9 with the minimal environment."