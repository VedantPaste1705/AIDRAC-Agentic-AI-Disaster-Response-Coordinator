const { createCanvas } = require('canvas');
const fs = require('fs');
const path = require('path');

const outputDir = path.join(__dirname, '..', 'public', 'icons');

function drawAidracIcon(ctx, size) {
  const center = size / 2;
  const radius = size * 0.42;

  // Background circle with gradient
  const bgGradient = ctx.createRadialGradient(center, center, 0, center, center, radius * 1.2);
  bgGradient.addColorStop(0, '#1e3a5f');
  bgGradient.addColorStop(1, '#0f1f3a');
  ctx.fillStyle = bgGradient;
  ctx.beginPath();
  ctx.arc(center, center, radius * 1.15, 0, Math.PI * 2);
  ctx.fill();

  // Shield shape
  const shieldWidth = radius * 1.6;
  const shieldHeight = radius * 1.8;
  const shieldX = center - shieldWidth / 2;
  const shieldY = center - shieldHeight / 2 + size * 0.02;

  // Shield path
  ctx.beginPath();
  ctx.moveTo(center, shieldY + shieldHeight);
  ctx.lineTo(shieldX, shieldY + shieldHeight * 0.65);
  ctx.bezierCurveTo(
    shieldX, shieldY + shieldHeight * 0.25,
    shieldX, shieldY,
    center, shieldY
  );
  ctx.bezierCurveTo(
    center, shieldY,
    shieldX + shieldWidth, shieldY,
    shieldX + shieldWidth, shieldY + shieldHeight * 0.25
  );
  ctx.bezierCurveTo(
    shieldX + shieldWidth, shieldY + shieldHeight * 0.25,
    shieldX + shieldWidth, shieldY + shieldHeight * 0.65,
    center, shieldY + shieldHeight
  );
  ctx.closePath();

  // Shield fill gradient
  const shieldGradient = ctx.createLinearGradient(shieldX, shieldY, shieldX + shieldWidth, shieldY + shieldHeight);
  shieldGradient.addColorStop(0, '#1e40af');
  shieldGradient.addColorStop(0.5, '#2563eb');
  shieldGradient.addColorStop(1, '#1e40af');
  ctx.fillStyle = shieldGradient;
  ctx.fill();

  // Shield border
  ctx.strokeStyle = '#3b82f6';
  ctx.lineWidth = size * 0.012;
  ctx.stroke();

  // Inner shield highlight
  ctx.beginPath();
  ctx.moveTo(center, shieldY + shieldHeight * 0.92);
  ctx.lineTo(shieldX + shieldWidth * 0.12, shieldY + shieldHeight * 0.6);
  ctx.bezierCurveTo(
    shieldX + shieldWidth * 0.12, shieldY + shieldHeight * 0.3,
    shieldX + shieldWidth * 0.12, shieldY + shieldHeight * 0.12,
    center, shieldY + shieldHeight * 0.1
  );
  ctx.bezierCurveTo(
    center, shieldY + shieldHeight * 0.12,
    shieldX + shieldWidth * 0.88, shieldY + shieldHeight * 0.12,
    shieldX + shieldWidth * 0.88, shieldY + shieldHeight * 0.3
  );
  ctx.bezierCurveTo(
    shieldX + shieldWidth * 0.88, shieldY + shieldHeight * 0.3,
    shieldX + shieldWidth * 0.88, shieldY + shieldHeight * 0.6,
    center, shieldY + shieldHeight * 0.92
  );
  ctx.closePath();

  const highlightGradient = ctx.createLinearGradient(shieldX, shieldY, shieldX, shieldY + shieldHeight);
  highlightGradient.addColorStop(0, 'rgba(59, 130, 246, 0.3)');
  highlightGradient.addColorStop(1, 'rgba(30, 64, 175, 0.05)');
  ctx.fillStyle = highlightGradient;
  ctx.fill();

  // Medical cross / plus sign in center
  const crossSize = size * 0.22;
  const crossThickness = size * 0.055;
  const crossX = center;
  const crossY = center + size * 0.02;

  // Cross background circle
  const crossBgGradient = ctx.createRadialGradient(crossX, crossY, 0, crossX, crossY, crossSize * 0.9);
  crossBgGradient.addColorStop(0, 'rgba(255, 255, 255, 0.15)');
  crossBgGradient.addColorStop(1, 'rgba(255, 255, 255, 0.03)');
  ctx.fillStyle = crossBgGradient;
  ctx.beginPath();
  ctx.arc(crossX, crossY, crossSize * 0.9, 0, Math.PI * 2);
  ctx.fill();

  // Cross vertical bar
  ctx.fillStyle = '#ffffff';
  ctx.beginPath();
  ctx.roundRect(
    crossX - crossThickness / 2,
    crossY - crossSize / 2,
    crossThickness,
    crossSize,
    crossThickness / 2
  );
  ctx.fill();

  // Cross horizontal bar
  ctx.beginPath();
  ctx.roundRect(
    crossX - crossSize / 2,
    crossY - crossThickness / 2,
    crossSize,
    crossThickness,
    crossThickness / 2
  );
  ctx.fill();

  // Subtle glow effect on cross
  ctx.shadowColor = '#60a5fa';
  ctx.shadowBlur = size * 0.03;
  ctx.fillStyle = '#ffffff';
  ctx.beginPath();
  ctx.roundRect(
    crossX - crossThickness / 2,
    crossY - crossSize / 2,
    crossThickness,
    crossSize,
    crossThickness / 2
  );
  ctx.fill();
  ctx.beginPath();
  ctx.roundRect(
    crossX - crossSize / 2,
    crossY - crossThickness / 2,
    crossSize,
    crossThickness,
    crossThickness / 2
  );
  ctx.fill();
  ctx.shadowBlur = 0;

  // Small dots at corners for "coordinator" feel
  const dotRadius = size * 0.018;
  const dotPositions = [
    [center - shieldWidth * 0.35, shieldY + shieldHeight * 0.25],
    [center + shieldWidth * 0.35, shieldY + shieldHeight * 0.25],
    [center - shieldWidth * 0.28, shieldY + shieldHeight * 0.75],
    [center + shieldWidth * 0.28, shieldY + shieldHeight * 0.75],
  ];

  ctx.fillStyle = '#3b82f6';
  dotPositions.forEach(([x, y]) => {
    ctx.beginPath();
    ctx.arc(x, y, dotRadius, 0, Math.PI * 2);
    ctx.fill();
  });

  // Text "AIDRAC" at bottom (for larger icon)
  if (size >= 512) {
    ctx.font = `bold ${size * 0.08}px Inter, sans-serif`;
    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('AIDRAC', center, shieldY + shieldHeight + size * 0.08);
  }
}

function generateIcon(size) {
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Enable high quality rendering
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';

  drawAidracIcon(ctx, size);

  const buffer = canvas.toBuffer('image/png');
  const outputPath = path.join(outputDir, `icon-${size}.png`);
  fs.writeFileSync(outputPath, buffer);
  console.log(`Generated ${outputPath} (${buffer.length} bytes)`);
}

console.log('Generating AIDRAC PWA icons...');
generateIcon(192);
generateIcon(512);
console.log('Done!');