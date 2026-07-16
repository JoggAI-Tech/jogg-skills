# Jogg API Endpoint Index

This reference is copied from the existing `jogg-api` skill. Its canonical paths use `/v2`; the local Jogg backend mounts the same operations under `/open/v2`. Smart Slides only uses voices, public avatars, `create_video_from_avatar`, and `avatar_video/{id}`.

Smart Slides always sends `voice.type="script"`. It never calls a standalone TTS operation or the custom-audio workflow.

## Identity And Quota

| Operation | Method | Path | Purpose | Key Inputs |
|---|---|---|---|---|
| `user-whoami` | `GET` | `/v2/user/whoami` | Read current account info | none |
| `user-quota-get` | `GET` | `/v2/user/remaining_quota` | Read remaining credits/quota | none |

## Voices, Avatars, Templates, Styles

| Operation | Method | Path | Purpose | Key Inputs |
|---|---|---|---|---|
| `voices-list` | `GET` | `/v2/voices` | List platform voices | `language`, `gender`, paging filters |
| `voices-custom-list` | `GET` | `/v2/voices/custom` | List cloned/custom voices | paging filters |
| `avatars-public-list` | `GET` | `/v2/avatars/public` | List public avatars | `aspect_ratio`, `style`, `gender`, `age`, `scene`, `ethnicity` |
| `avatars-custom-list` | `GET` | `/v2/avatars/custom` | List custom avatars | paging filters |
| `avatars-photo-list` | `GET` | `/v2/avatars/photo_avatars` | List photo avatars | paging filters |
| `avatars-product-list` | `GET` | `/v2/avatars/product_avatars` | List product avatars | `aspect_ratio`, paging filters |
| `templates-list` | `GET` | `/v2/templates` | List index templates | `aspect_ratio` |
| `templates-custom-list` | `GET` | `/v2/templates/custom` | List custom templates | `aspect_ratio` |
| `template-custom-get` | `GET` | `/v2/template/custom/{id}` | Read template details and variables | path `id` |
| `visual-styles-list` | `GET` | `/v2/visual_styles` | List product video visual styles | `aspect_ratio` |
| `music-list` | `GET` | `/v2/musics` | List background music | paging filters |

## Assets And Scripts

| Operation | Method | Path | Purpose | Key Inputs |
|---|---|---|---|---|
| `asset-upload-sign` | `POST` | `/v2/upload/asset` | Get signed upload URL | `filename`, `content_type`, `file_size` |
| `ai-scripts-create` | `POST` | `/v2/ai_scripts` | Submit async script generation | `language`, `video_length_seconds`, `script_style`, `product_info` |
| `ai-scripts-result-get` | `GET` | `/v2/ai_scripts/results/{task_id}` | Poll script generation result | path `task_id` |

## Avatar Creation

| Operation | Method | Path | Purpose | Key Inputs |
|---|---|---|---|---|
| `photo-avatar-generate` | `POST` | `/v2/photo_avatar/photo/generate` | Generate photo avatar images | `age`, `avatar_style`, `gender`, `model`, `aspect_ratio`, optional `image_url` |
| `photo-avatar-status-get` | `GET` | `/v2/photo_avatar/photo` | Poll generated photo avatar images | query `photo_id` |
| `photo-avatar-motion-add` | `POST` | `/v2/photo_avatar/add_motion` | Turn photo avatar image into animated avatar | `image_url`, `name`, `voice_id`, `model` |
| `photo-avatar-motion-get` | `GET` | `/v2/photo_avatar` | Poll photo avatar motion task | query `motion_id` |
| `product-avatar-image-generate` | `POST` | `/v2/product_avatar/generation` | Generate product avatar images | `product_image_url`, `avatar_source`, `quality`, `aspect_ratio`, `num_images` |
| `product-avatar-image-status-get` | `GET` | `/v2/product_avatar/generation/{batch_id}` | Poll product avatar image batch | path `batch_id` |
| `product-avatar-motion-add` | `POST` | `/v2/product_avatar/add_motion` | Turn generated image into product avatar | `generation_id`, `name`, `voice_id`, `description` |
| `product-avatar-motion-get` | `GET` | `/v2/product_avatar` | Poll product avatar motion task | query `motion_id` |

## Video Creation

| Operation | Method | Path | Purpose | Key Inputs |
|---|---|---|---|---|
| `avatar-video-create` | `POST` | `/v2/create_video_from_avatar` | Create talking avatar video | `avatar`, `voice`, `aspect_ratio`, `screen_style` |
| `avatar-video-get` | `GET` | `/v2/avatar_video/{id}` | Poll avatar video result | path `id` |
| `product-create` | `POST` | `/v2/product` | Create product from URL or structured details | `url` or `name`, optional `description`, `target_audience`, `media` |
| `product-update` | `PUT` | `/v2/product` | Refine product info before rendering | `product_id`, optional updates |
| `product-video-create` | `POST` | `/v2/create_video_from_product` | Render product video directly | `product_id`, `video_spec`, `avatar`, `voice`, `audio`, `script` |
| `product-video-preview-submit` | `POST` | `/v2/create_video_from_product/preview_list` | Generate previews for multiple styles | `product_id`, `visual_styles`, `video_spec`, `avatar`, `voice`, `audio`, `script` |
| `product-video-preview-render` | `POST` | `/v2/create_video_from_product/render_single_preview` | Render final video from preview | `preview_id` |
| `product-video-get` | `GET` | `/v2/product_video/{product_video_id}` | Poll product video result | path `product_video_id` |
| `product-previews-list` | `GET` | `/v2/product_previews` | Browse existing previews | paging/status filters |
| `product-videos-list` | `GET` | `/v2/product_videos` | Browse rendered product videos | paging/status filters |
| `template-video-create` | `POST` | `/v2/create_video_with_template` | Render template-based video | `template_id`, `voice_language`, `variables` |
| `template-video-get` | `GET` | `/v2/template_video/{video_id}` | Poll template video result | path `video_id` |
| `template-videos-list` | `GET` | `/v2/template_videos` | Browse template videos | paging/status filters |
| `video-translate-create` | `POST` | `/v2/video_translate/` | Submit video translation | `video_url`, `output_language`, optional `output_voice`, subtitles |
| `video-translate-get` | `GET` | `/v2/video_translate/{video_translate_id}` | Poll translation result | path `video_translate_id` |
| `video-translate-target-languages-list` | `GET` | `/v2/video_translate/target_languages` | List supported target languages | none |

## Webhooks

| Operation | Method | Path | Purpose | Key Inputs |
|---|---|---|---|---|
| `webhook-endpoints-list` | `GET` | `/v2/endpoints` | List existing webhook endpoints | none |
| `webhook-endpoint-create` | `POST` | `/v2/endpoint` | Create webhook endpoint | `url`, `events`, `status` |
| `webhook-endpoint-update` | `PUT` | `/v2/endpoint/{endpoint_id}` | Update webhook endpoint | path `endpoint_id`, body `url`, `events`, `status` |
| `webhook-endpoint-delete` | `DELETE` | `/v2/endpoint/{endpoint_id}` | Delete webhook endpoint | path `endpoint_id` |
| `webhook-events-list` | `GET` | `/v2/events` | List subscribable event types | none |

## Polling Guardrails

- Polling is only allowed on async status endpoints.
- The runtime clamps poll interval to at least `10s`.
- Every poll loop is bounded by both `max_wait_seconds` and `max_poll_attempts`.
- When the limit is hit, the runtime returns the last known payload with `poll_timeout: true`.
