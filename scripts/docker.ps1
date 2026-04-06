param(
    [ValidateSet("build", "up", "down", "logs", "ps", "rebuild")]
    [string]$Action = "up"
)

$composeFile = "docker/docker-compose.yml"

switch ($Action) {
    "build" {
        docker build -t sinhala-learn-backend:latest .
        break
    }
    "up" {
        docker compose -f $composeFile up -d
        break
    }
    "down" {
        docker compose -f $composeFile down
        break
    }
    "logs" {
        docker compose -f $composeFile logs -f api
        break
    }
    "ps" {
        docker compose -f $composeFile ps
        break
    }
    "rebuild" {
        docker compose -f $composeFile up --build -d
        break
    }
}