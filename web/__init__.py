"""Heroku deployment adapter for RCM-MC — additive shim over `rcm_mc.server`.

Adapts the existing 15,327-LOC stdlib HTTP app to Heroku conventions
(`$PORT`, SIGTERM, first-boot admin from env). Nothing under `rcm_mc/`
modified.
"""
