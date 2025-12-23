const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const svgPath = path.join(__dirname, '..', 'public', 'icon.svg');
const outputDir = path.join(__dirname, '..', 'public', 'icons');

// Read SVG
const svgContent = fs.readFileSync(svgPath, 'utf8');

// Remove animations for static PNG
const staticSvg = svgContent.replace(/<animate[^>]*\/>/g, '');

const sizes = [16, 48, 128];

async function generateIcons() {
  // Ensure output directory exists
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  for (const size of sizes) {
    const outputPath = path.join(outputDir, `icon${size}.png`);

    await sharp(Buffer.from(staticSvg))
      .resize(size, size)
      .png()
      .toFile(outputPath);

    console.log(`Generated: icon${size}.png`);
  }

  console.log('Done!');
}

generateIcons().catch(console.error);
