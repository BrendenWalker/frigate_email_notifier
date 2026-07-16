# Frigate Email Notifier

Slim Docker service that listens to Frigate MQTT events and sends email alerts with embedded snapshot images during a configurable night window.

## Requirements

- Docker and Docker Compose
- MQTT broker reachable from the container (Frigate MQTT or Mosquitto)
- SMTP server credentials

## Setup

1. Copy the example environment file and edit values:

```bash
cp .env.example .env
```

2. Set `MQTT_HOST` to your broker hostname or IP. On Docker Desktop you can use `host.docker.internal` to reach a broker on the host machine.

3. Configure SMTP and alert settings in `.env`.

4. Start the service:

```bash
docker compose up --build -d
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_HOST` | required | MQTT broker hostname |
| `MQTT_PORT` | `1883` | MQTT port |
| `MQTT_USER` | empty | Optional MQTT username |
| `MQTT_PASS` | empty | Optional MQTT password |
| `MQTT_TOPIC_PREFIX` | `frigate` | Frigate topic prefix |
| `SMTP_HOST` | required | SMTP server |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | required | SMTP username |
| `SMTP_PASS` | required | SMTP password |
| `SMTP_FROM` | required | From address |
| `SMTP_TO` | required | Comma-separated recipients |
| `SMTP_USE_TLS` | `true` | Use STARTTLS |
| `ALERT_START_HOUR` | `19` | Night window start (local time) |
| `ALERT_END_HOUR` | `7` | Night window end (local time) |
| `EXCLUDED_LABELS` | `bird` | Comma-separated labels to skip |
| `TZ` | `UTC` | IANA timezone used for event times and the alert window |

## Behavior

- Subscribes to `{MQTT_TOPIC_PREFIX}/#`
- Stores the latest `frigate/events` payload
- On a matching `{prefix}/{camera}/{label}/snapshot` message, sends email when:
  - The label is not excluded (default: `bird`)
  - The event has a clip or snapshot
  - The event end time falls in the night window (default 7 PM–7 AM local time)
  - That Frigate event has not already produced an email

Logs are written to stdout for Docker.

## Frigate MQTT

Ensure Frigate publishes to MQTT. Example Frigate config:

```yaml
mqtt:
  host: mosquitto
  user: frigate
  password: your-password
```

## Logs

```bash
docker compose logs -f frigate-email-notifier
```

## Portainer

Use [`portainer-stack.example.yml`](portainer-stack.example.yml) as a starting point.

1. In Portainer, go to **Stacks** → **Add stack**.
2. Choose **Git repository** (point at this repo, compose path `portainer-stack.example.yml`) or paste the file into the **Web editor**.
3. Under **Environment variables**, add the required values (same as `.env.example`). Example:

```env
MQTT_HOST=mosquitto
MQTT_PORT=1883
MQTT_USER=frigate
MQTT_PASS=your-mqtt-password
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=alerts@example.com
SMTP_PASS=your-smtp-password
SMTP_FROM=alerts@example.com
SMTP_TO=you@example.com
TZ=America/Los_Angeles
```

4. If your MQTT broker is in another stack, uncomment the external network section in the stack file and attach the service to that network so `MQTT_HOST` can be the broker service name.

Deploy the stack from Portainer; Portainer will build the image from the repo context on first deploy.
