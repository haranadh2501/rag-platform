$ErrorActionPreference = "Continue"

$runRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$resultsDir = Join-Path $runRoot "results"
$logsDir = Join-Path $runRoot "logs"
New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$n8nUrl = "https://n8n-production-c637.up.railway.app/webhook/retrieve"
$tenantId = "22222222-2222-2222-2222-222222222222"
$batchSize = 5
$totalBatches = 30
$maxBatchAttempts = 2
$failures = @()
$python = "C:\Users\yasha\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

try {

for ($batch = 1; $batch -le $totalBatches; $batch++) {
    $batchSucceeded = $false
    for ($attempt = 1; $attempt -le $maxBatchAttempts; $attempt++) {
        $stdout = Join-Path $logsDir ("batch_{0:D2}_attempt_{1}_stdout.log" -f $batch, $attempt)
        $stderr = Join-Path $logsDir ("batch_{0:D2}_attempt_{1}_stderr.log" -f $batch, $attempt)
        $started = Get-Date -Format o
        Add-Content -Path (Join-Path $runRoot "run_progress.log") -Value "START batch=$batch attempt=$attempt at=$started"

        & $python -m evaluation.run_eval --suite-dataset `
            --n8n-url $n8nUrl `
            --n8n-tenant-id $tenantId `
            --skip-ragas `
            --batch-size $batchSize `
            --batch-index $batch `
            --timeout 240 `
            --max-chunks-per-query 5 `
            --n8n-retries 8 `
            --results-dir $resultsDir `
            1> $stdout 2> $stderr

        $exitCode = $LASTEXITCODE
        $ended = Get-Date -Format o
        Add-Content -Path (Join-Path $runRoot "run_progress.log") -Value "END batch=$batch attempt=$attempt exit=$exitCode at=$ended"

        if ($exitCode -eq 0) {
            $batchSucceeded = $true
            break
        }
        Start-Sleep -Seconds 15
    }

    if (-not $batchSucceeded) {
        $failures += $batch
        Add-Content -Path (Join-Path $runRoot "run_progress.log") -Value "FAILED batch=$batch"
    }
}

if ($failures.Count -gt 0) {
    $failureText = $failures -join ","
    Set-Content -Path (Join-Path $runRoot "failed_batches.txt") -Value $failureText -Encoding ascii
    exit 1
}

Set-Content -Path (Join-Path $runRoot "completed.txt") -Value (Get-Date -Format o) -Encoding ascii
exit 0
} catch {
    Set-Content -Path (Join-Path $runRoot "fatal_error.txt") -Value $_.Exception.ToString() -Encoding utf8
    exit 1
}
