$body = @{
    model     = "typesafe-ai/jev"
    state     = "I was charged twice for my subscription this month. Please reverse the second charge."
    questions = @{
        refund = @{
            type         = "boolean"
            instructions = "Is the customer asking for money back?"
        }
    }
} | ConvertTo-Json -Depth 6

$response = Invoke-RestMethod `
    -Uri "https://ai-gateway.vercel.sh/v1/evaluate" `
    -Method Post `
    -Headers @{ Authorization = "Bearer $env:AI_GATEWAY_API_KEY" } `
    -ContentType "application/json" `
    -Body $body

$response | ConvertTo-Json -Depth 10
