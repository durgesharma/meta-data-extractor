param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)
python "$PSScriptRoot\extractor.py" @ScriptArgs
