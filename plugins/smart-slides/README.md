# smart-slides Codex Plugin

This personal Codex plugin orchestrates local Jogg and Podcastor Video Studio services. It does not modify either source repository.

Set up local Jogg authentication once by logging in to the local Jogg web application and exposing its JWT as `JOGG_WEB_TOKEN`, or provide an existing `JOGG_API_KEY`. The runner retrieves the OpenAPI key in memory and never records either credential in its run state.

Run `bash scripts/video-studio.sh preflight` before the first render. See `skills/smart-slides/SKILL.md` for command examples and configuration.
