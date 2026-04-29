[CmdletBinding()]
param(
    [string]$Url = "http://localhost:30090"
)

Start-Process $Url
