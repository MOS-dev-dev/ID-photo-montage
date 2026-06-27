import React from 'react';

function Controls({ frameConfig, imageAdjust, onAdjustChange, onGenerate, onSaveFrame, onResetPosition, isGenerating, disabled }) {
  const handleChange = (e) => {
    const { name, value } = e.target;
    onAdjustChange(prev => ({
      ...prev,
      [name]: parseFloat(value)
    }));
  };

  return (
    <div className="bg-white p-6 rounded shadow-sm">
      <div className="mb-6 border-b pb-4">
        <h2 className="text-xl font-bold mb-4">Frame State</h2>
        <div className="grid grid-cols-2 gap-2 text-sm text-gray-600 bg-gray-50 p-3 rounded">
          <div><span className="font-semibold text-gray-800">X:</span> {frameConfig?.x?.toFixed(1) || 0}</div>
          <div><span className="font-semibold text-gray-800">Y:</span> {frameConfig?.y?.toFixed(1) || 0}</div>
          <div><span className="font-semibold text-gray-800">Scale:</span> {frameConfig?.scale?.toFixed(2) || 0}</div>
          <div><span className="font-semibold text-gray-800">Rotation:</span> {frameConfig?.rotation?.toFixed(1) || 0}°</div>
          <div><span className="font-semibold text-gray-800">W:</span> {frameConfig?.width?.toFixed(1) || 0}</div>
          <div><span className="font-semibold text-gray-800">H:</span> {frameConfig?.height?.toFixed(1) || 0}</div>
        </div>
        <div className="flex gap-2 mt-3">
          <button 
            onClick={onResetPosition}
            disabled={disabled}
            className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 text-xs py-1.5 rounded disabled:opacity-50"
          >
            Reset Pos
          </button>
          <button 
            onClick={onSaveFrame}
            disabled={disabled}
            className="flex-1 bg-blue-100 hover:bg-blue-200 text-blue-800 text-xs py-1.5 rounded disabled:opacity-50"
          >
            Save Frame
          </button>
        </div>
      </div>
      
      <h2 className="text-xl font-bold mb-6 border-b pb-2">Adjustments</h2>
      
      <div className="space-y-6">
        <div>
          <div className="flex justify-between text-sm mb-1">
            <label className="font-medium text-gray-700">Brightness</label>
            <span className="text-gray-500">{imageAdjust.brightness.toFixed(2)}</span>
          </div>
          <input 
            type="range" 
            name="brightness"
            min="0.90" max="1.10" step="0.01" 
            value={imageAdjust.brightness}
            onChange={handleChange}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            disabled={disabled}
          />
        </div>
        
        <div>
          <div className="flex justify-between text-sm mb-1">
            <label className="font-medium text-gray-700">Contrast</label>
            <span className="text-gray-500">{imageAdjust.contrast.toFixed(2)}</span>
          </div>
          <input 
            type="range" 
            name="contrast"
            min="0.8" max="1.5" step="0.05" 
            value={imageAdjust.contrast}
            onChange={handleChange}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            disabled={disabled}
          />
        </div>
        
        <div>
          <div className="flex justify-between text-sm mb-1">
            <label className="font-medium text-gray-700">Saturation</label>
            <span className="text-gray-500">{imageAdjust.saturation.toFixed(2)}</span>
          </div>
          <input 
            type="range" 
            name="saturation"
            min="0.5" max="1.5" step="0.05" 
            value={imageAdjust.saturation}
            onChange={handleChange}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            disabled={disabled}
          />
        </div>
      </div>
      
      <button
        onClick={onGenerate}
        disabled={disabled || isGenerating}
        className={`w-full mt-8 py-3 px-4 font-bold rounded-lg shadow transition-colors ${
          disabled || isGenerating 
            ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
            : 'bg-blue-600 hover:bg-blue-700 text-white'
        }`}
      >
        {isGenerating ? (
          <span className="flex items-center justify-center">
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Processing...
          </span>
        ) : 'GENERATE CARD'}
      </button>
    </div>
  );
}

export default Controls;
