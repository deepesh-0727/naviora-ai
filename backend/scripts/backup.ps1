$ErrorActionPreference = 'Stop'
$backupRestoreScript = Join-Path $PSScriptRoot 'backup_restore.py'
python $backupRestoreScript backup @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
