# Jogg API Workflow Index

These workflows mirror the existing `jogg-api` guides. Smart Slides uses the public `https://api.jogg.ai/v2` API and implements bounded avatar-video polling in `scripts/smart-slides.sh` so run checkpoints include every shot's `video_id`.

## `upload-media`

Use when the user has a local file and needs an `asset_url`.

Steps:
1. `POST /v2/upload/asset`
2. `PUT sign_url`
3. Return `asset_url`

## `ai-scripts`

Use when the user wants generated marketing scripts.

Steps:
1. Submit `POST /v2/ai_scripts`
2. Poll `GET /v2/ai_scripts/results/{task_id}`
3. Return generated scripts or the latest task state

## `create-photo-avatar`

Use when the user wants a photo avatar image set.

Steps:
1. Optional local file upload for `image_path`
2. Submit `POST /v2/photo_avatar/photo/generate`
3. Poll `GET /v2/photo_avatar/photo?photo_id=...`
4. Return `image_url_list`

## `photo-avatar-motion`

Use when the user wants to turn a photo avatar image into an animated avatar.

Steps:
1. Resolve `image_url` directly or by polling a `photo_id`
2. Submit `POST /v2/photo_avatar/add_motion`
3. Poll `GET /v2/photo_avatar?motion_id=...`
4. Return `avatar_id`, preview URL, and status

## `avatar-video`

Use when the user wants a standard talking avatar video.

Steps:
1. Optional local upload for `voice.audio_path`
2. Submit `POST /v2/create_video_from_avatar`
3. Poll `GET /v2/avatar_video/{id}`
4. Return final `video_url` when ready

## `avatar-video-with-photo-avatar`

Same as `avatar-video`, but forces `avatar.avatar_type = 1`.

## `avatar-video-with-custom-audio`

Same as `avatar-video`, but forces `voice.type = "audio"` and uploads `voice.audio_path` when needed.

## `avatar-video-transparent`

Same as `avatar-video`, but defaults `screen_style = 3` for transparent output unless the caller explicitly sets it.

## `url-to-video`

Use when the user wants product URL/details to become a product video.

Direct mode:
1. `POST /v2/product`
2. Optional `PUT /v2/product`
3. `POST /v2/create_video_from_product`
4. Poll `GET /v2/product_video/{product_video_id}`

Preview mode:
1. `POST /v2/product`
2. Optional `PUT /v2/product`
3. `POST /v2/create_video_from_product/preview_list`
4. Pick one `preview_id`
5. `POST /v2/create_video_from_product/render_single_preview`
6. Poll `GET /v2/product_video/{product_video_id}`

## `create-template-video`

Use when the user already has a template and variable payload.

Steps:
1. Optional local asset upload for `variables[].properties.local_path`
2. `POST /v2/create_video_with_template`
3. Poll `GET /v2/template_video/{video_id}`

## `video-translation`

Use when the user wants to translate a source video into another language.

Steps:
1. Optional local upload for `video_path`
2. `POST /v2/video_translate/`
3. Poll `GET /v2/video_translate/{video_translate_id}`

## `product-avatar`

Use when the user wants to generate a product avatar from product imagery.

Steps:
1. Optional local upload for `product_image_path`
2. `POST /v2/product_avatar/generation`
3. Poll `GET /v2/product_avatar/generation/{batch_id}`
4. Choose one completed `generation_id`
5. `POST /v2/product_avatar/add_motion`
6. Poll `GET /v2/product_avatar?motion_id=...`

## `webhook-integration`

Use when the user wants to manage callback endpoints.

Supported actions:
- `list`
- `events`
- `create`
- `update`
- `delete`

## `get-result`

Use when the user already has an async identifier and only wants the latest result.

Supported `kind` values:
- `ai-scripts`
- `avatar-video`
- `photo-avatar`
- `photo-avatar-motion`
- `product-avatar-image`
- `product-avatar-motion`
- `product-video`
- `template-video`
- `video-translation`
