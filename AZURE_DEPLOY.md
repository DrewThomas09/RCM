# RETIRED — production moved to DigitalOcean

> **This runbook is retired.** PEdesk production (**https://pedesk.app**)
> runs on a **DigitalOcean droplet**: the app lives in `/opt/RCM` under the
> `pedesk.service` systemd unit behind Caddy (Let's Encrypt TLS), and every
> push to `main` auto-deploys through
> [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) after the
> test gate.
>
> - Droplet setup & operations: [RCM_MC/docs/DIGITALOCEAN_DEPLOYMENT.md](RCM_MC/docs/DIGITALOCEAN_DEPLOYMENT.md)
> - Push-to-main pipeline: [RCM_MC/docs/AUTODEPLOY.md](RCM_MC/docs/AUTODEPLOY.md)
> - Legacy docker-compose alternative (any Ubuntu VM): [RCM_MC/deploy/PEDESK_DEPLOY.md](RCM_MC/deploy/PEDESK_DEPLOY.md)
>
> The Azure VM quickstart that used to live here described the pre-migration
> topology and has been removed so nobody follows a dead runbook. The full
> historical assessment remains in [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md)
> (marked historical).

This file is kept as a tombstone because older docs, PRs, and bookmarks link
to it.
