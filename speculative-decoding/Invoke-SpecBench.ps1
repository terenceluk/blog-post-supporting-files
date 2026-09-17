param(
    [Parameter(Mandatory)] [string] $Model,
    [Parameter(Mandatory)] [string] $DraftModel,
    [int] $Runs = 3,
    [string] $BaseUrl = "http://localhost:1234"
)

$prompts = Get-Content .\prompts.json -Raw | ConvertFrom-Json

function Invoke-Completion {
    param([string] $Prompt, [string] $Draft)

    $body = @{
        model       = $Model
        messages    = @(
            @{
                role    = "user"
                content = $Prompt
            }
        )
        temperature = 0
        max_tokens  = 1024
    }
    if ($Draft) { $body.draft_model = $Draft }

    Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v0/chat/completions" `
        -ContentType "application/json" -Body ($body | ConvertTo-Json -Depth 5)
}

# One throwaway request in each mode so model loading time is not measured
Invoke-Completion -Prompt "Reply with the word ready." | Out-Null
Invoke-Completion -Prompt "Reply with the word ready." -Draft $DraftModel | Out-Null

$results = foreach ($entry in $prompts) {
    foreach ($run in 1..$Runs) {
        foreach ($draft in @($null, $DraftModel)) {
            $response = Invoke-Completion -Prompt $entry.prompt -Draft $draft
            $message = $response.choices[0].message

            [pscustomobject]@{
                Prompt          = $entry.name
                Mode            = if ($draft) { "with draft" } else { "without draft" }
                TokensPerSecond = $response.stats.tokens_per_second
                AcceptedDraft   = [int] $response.stats.accepted_draft_tokens_count
                TotalDraft      = [int] $response.stats.total_draft_tokens_count
                Output          = "$($message.reasoning_content)$($message.content)"
            }
        }
    }
}

$results | Select-Object Prompt, Mode, TokensPerSecond, AcceptedDraft, TotalDraft |
    Export-Csv ".\results-$($Model -replace '[^\w.-]', '_').csv" -NoTypeInformation

$results | Group-Object Prompt | ForEach-Object {
    $without = $_.Group | Where-Object Mode -eq "without draft"
    $with = $_.Group | Where-Object Mode -eq "with draft"
    $withoutTps = ($without | Measure-Object TokensPerSecond -Average).Average
    $withTps = ($with | Measure-Object TokensPerSecond -Average).Average
    $accepted = ($with | Measure-Object AcceptedDraft -Sum).Sum
    $drafted = ($with | Measure-Object TotalDraft -Sum).Sum

    [pscustomobject]@{
        Prompt          = $_.Name
        WithoutDraftTps = [math]::Round($withoutTps, 1)
        WithDraftTps    = [math]::Round($withTps, 1)
        Speedup         = [math]::Round($withTps / $withoutTps, 2)
        AcceptanceRate  = if ($drafted) { [math]::Round($accepted / $drafted, 2) } else { "n/a" }
        SameOutput      = @($_.Group.Output | Select-Object -Unique).Count -eq 1
    }
} | Format-Table -AutoSize