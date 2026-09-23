# Generated car catalogue images

Generated with the built-in image-generation tool, one individual image per car in `vehicles/management/commands/seed_showcase.py`.

Assets are saved under `media/vehicles/ai-showcase/`, with filenames matching each demo registration number in lowercase. The original generated PNGs are preserved. Run `python manage.py attach_showcase_images` to validate and attach available images to demo listings that do not already have an image. It never replaces existing uploaded photos.

## Prompt set

Each prompt names the listing's year, brand and model and requests a photorealistic studio rendering of its stock exterior: one complete car, front three-quarter view, centered with margins, landscape 3:2, pale grey seamless studio, softbox reflections and a subtle floor shadow. Ferrari images use red paint, Lamborghini images use yellow, and other images use silver or graphite. No people, overlay text, prices, watermark or collage.

These are AI-generated illustrations, not verified photographs or evidence of real fleet availability. Exact trim, regional configuration and model details may vary. The catalogue cards and detail pages identify these images as AI-generated. Replace them with your own actual fleet photos when offering real cars for rental.
