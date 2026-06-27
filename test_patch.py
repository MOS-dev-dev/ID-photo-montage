from PIL import Image, ImageDraw, ImageFilter

# Open blank template
img = Image.open('blank_template.png')

# Create a patch to cover the smudge
patch = Image.new('RGBA', (490, 680), (0,0,0,0))
draw = ImageDraw.Draw(patch)

# The smudge is roughly around x=20 to 450, y=20 to 500 inside the 490x680 box
# Let's draw a rounded rectangle with the average background color
bg_color = (210, 215, 220, 255) # Light gray/blue from the pattern
draw.rounded_rectangle([10, 10, 480, 600], radius=50, fill=bg_color)

# Blur the patch heavily to make it fade smoothly
patch = patch.filter(ImageFilter.GaussianBlur(30))

# Paste the patch over the template at the photo location
img.alpha_composite(patch, (445, 960))

# Save the debug image
img.crop((445, 960, 445+490, 960+680)).save('_debug_patch_crop.png')
img.save('_debug_patch_full.png')
