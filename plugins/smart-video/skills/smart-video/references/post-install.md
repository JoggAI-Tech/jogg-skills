# Installation Handoff And First Use

These instructions are shipped inside the plugin for the installing Agent and
the Agent handling the user's first conversation.

## Installing Agent

1. Verify through the host's plugin listing that the intended plugin version is
   installed and enabled. A downloaded archive or an unsuccessful installation
   is not an installed plugin. Report installation failures in the current chat.
2. Once installation succeeds, give brief usage guidance. If the user requested
   a new chat after installation, use the host's conversation creation tool with
   the user's current project and normal local environment. Preserve any stated
   preference for post-install handoff; do not ask the user to choose again.
3. Include the installed plugin identity and the first-use instructions below
   in the new chat's initial prompt. Ask its Agent to load the installed Smart
   Video Skill, greet the user in their language, provide the examples, and wait
   for a video request. Do not copy development checkout paths or old Skill text.
4. After creation succeeds, use the host's navigation tool to show the new chat
   and return its actual link or host-supported created-chat indicator. Do not
   say it opened if navigation failed. If conversation tools are unavailable,
   show the guidance in the current chat and explain that the user can start a
   new chat to load the installed plugin. Do not substitute a Settings page.

The plugin has no standalone chat-creation hook: this handoff is executed by
the installing Agent using host tools. Ordinary marketplace installation without
an Agent does not automatically run this document. Never invent a successful
handoff or run a launcher command to simulate it. Create one chat per requested
handoff; do not create another on every Skill invocation or resumed task.

## First Conversation

Say that Smart Video is installed and offer a few natural requests in the user's
language, for example:

- Make a 60-second Chinese explainer about solar energy, landscape, with subtitles.
- Help me write the script and storyboard first.
- Open my existing video project, edit its subtitles, and export an MP4.

Briefly explain that the Agent prepares missing tools when the task needs them,
and confirms the script/storyboard before production. Online generation can
require authentication and API Credits; discuss that when the task needs it.
Then wait for the user's request. Do not start a sample production automatically.

Onboarding requires no service startup, dependency checks, system installers,
model downloads, Settings page, browser, login, or paid generation. Once a real
request arrives, use the Skill's Chat-First Preparation flow for that capability.
