import React, { useEffect, useRef } from 'react';
import { fabric } from 'fabric';

function CanvasEditor({ imageUrl, frameConfig, onFrameChange }) {
  const canvasRef = useRef(null);
  const fabricRef = useRef(null);
  const imgRef = useRef(null);

  useEffect(() => {
    // Initialize Fabric.js canvas
    if (!fabricRef.current) {
      fabricRef.current = new fabric.Canvas(canvasRef.current, {
        width: 490,
        height: 650,
        backgroundColor: '#f3f4f6'
      });
      
      // Set template as overlay
      fabric.Image.fromURL('/template.png', function(img) {
        img.set({
          left: 0,
          top: 0,
          scaleX: 490 / img.width,
          scaleY: 650 / img.height,
          selectable: false,
          evented: false,
          opacity: 0.8 // slight opacity so user can see what's being cropped
        });
        fabricRef.current.setOverlayImage(img, fabricRef.current.renderAll.bind(fabricRef.current));
      });
      
      // Add mouse wheel zoom for active object
      fabricRef.current.on('mouse:wheel', function(opt) {
        const activeObj = fabricRef.current.getActiveObject();
        if (activeObj && activeObj.type === 'image') {
          var delta = opt.e.deltaY;
          var newScale = activeObj.scaleX * (0.999 ** delta);
          
          // To scale from the center of the object instead of top-left,
          // we should temporarily set origin to center, scale, then restore.
          // But actually, just scaling it is fine since user can drag it back.
          // Let's just scale it.
          activeObj.scale(newScale);
          activeObj.setCoords();
          fabricRef.current.renderAll();
          activeObj.fire('modified');
        }
        opt.e.preventDefault();
        opt.e.stopPropagation();
      });
    }

    const canvas = fabricRef.current;

    // Load Portrait
    if (imageUrl) {
      fabric.Image.fromURL(imageUrl, (img) => {
        // Clear previous images
        canvas.getObjects('image').forEach(obj => canvas.remove(obj));
        
        // Scale down initially to fit canvas
        const scaleX = 490 / img.width;
        const scaleY = 650 / img.height;
        const initScale = Math.min(scaleX, scaleY) * 0.95; // 95% of canvas to fit nicely
        
        img.set({
          left: (490 - img.width * initScale) / 2,
          top: (650 - img.height * initScale) / 2,
          scaleX: initScale,
          scaleY: initScale,
          cornerColor: '#3b82f6',
          cornerStrokeColor: '#3b82f6',
          borderColor: '#3b82f6',
          cornerSize: 12,
          transparentCorners: false
        });
        
        imgRef.current = img;
        canvas.add(img);
        canvas.setActiveObject(img);
        canvas.renderAll();
        
        const updateFrame = () => {
          onFrameChange(prev => ({
            ...prev,
            x: img.left,
            y: img.top,
            scale: img.scaleX,
            rotation: img.angle,
            width: img.getScaledWidth(),
            height: img.getScaledHeight(),
            canvas_width: 490,
            canvas_height: 650,
            timestamp: Date.now()
          }));
        };
        
        img.on('modified', updateFrame);
        updateFrame(); // initial update
      }, { crossOrigin: 'anonymous' });
    }

    return () => {
      if (fabricRef.current) {
        fabricRef.current.dispose();
        fabricRef.current = null;
      }
    };
  }, [imageUrl, onFrameChange]);

  useEffect(() => {
    if (frameConfig?.reset && imgRef.current && fabricRef.current) {
      imgRef.current.set({
        left: (490 - imgRef.current.width * imgRef.current.scaleX) / 2, // will be slightly off if initScale is not saved, but good enough for reset
        top: (650 - imgRef.current.height * imgRef.current.scaleY) / 2,
        angle: 0
      });
      imgRef.current.setCoords();
      fabricRef.current.renderAll();
      imgRef.current.fire('modified');
    }
  }, [frameConfig?.reset]);

  return (
    <div className="border shadow-inner bg-gray-50 overflow-hidden" style={{ width: 490, height: 650 }}>
      <canvas ref={canvasRef} />
    </div>
  );
}

export default CanvasEditor;
