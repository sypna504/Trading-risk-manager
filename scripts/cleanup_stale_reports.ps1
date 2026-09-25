$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$stale = @(
  "AUDIT_REPORT.md",
  "BUG_REPORT.md",
  "CHANGES.md",
  "EXECUTIVE_SUMMARY.md",
  "FUNCTIONAL_VALIDATION.md",
  "MODEL_AUDIT.md",
  "PROMOTION_VALIDATION.md",
  "RUNTIME_FIX.md",
  "RUNTIME_FIX_V6.md",
  "RUNTIME_FIX_V7.md",
  "VALIDATION_RESULTS.md",
  "TEST_RESULTS.txt",
  ".env.example.outcome-additions"
)
foreach ($name in $stale) {
    if (Test-Path $name) {
        Remove-Item $name -Force
        Write-Host "removed stale file: $name"
    }
}
