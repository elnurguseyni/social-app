#!/usr/bin/env bash
set -euo pipefail

action="${1:-}"

case "$action" in
  start)
    workflow="social-app-morning-start"
    ;;
  stop)
    workflow="social-app-evening-stop"
    ;;
  *)
    echo "Usage: $0 {start|stop}" >&2
    exit 1
    ;;
esac

workflow_arn="arn:aws:states:eu-central-1:117173314642:stateMachine:$workflow"

execution_arn=$(aws stepfunctions start-execution \
  --state-machine-arn "$workflow_arn" \
  --input '{}' \
  --region eu-central-1 \
  --profile social-app \
  --query executionArn \
  --output text \
  --no-cli-pager)

echo "Started execution: $execution_arn"

while true; do
  status=$(aws stepfunctions describe-execution \
    --execution-arn "$execution_arn" \
    --region eu-central-1 \
    --profile social-app \
    --query status \
    --output text \
    --no-cli-pager)

  echo "Current status: $status"

  case "$status" in
    SUCCEEDED)
      echo "App $action workflow completed."
      exit 0
      ;;
    RUNNING)
      sleep 30
      ;;
    *)
      echo "Workflow ended with unexpected or unsuccessful status: $status" >&2
        aws stepfunctions describe-execution \
        --execution-arn "$execution_arn" \
        --region eu-central-1 \
        --profile social-app \
        --query '{Status:status,Error:error,Cause:cause}' \
        --output json \
        --no-cli-pager >&2
      exit 1
      ;;
  esac
done