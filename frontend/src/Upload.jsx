import React, { useRef } from 'react';

function Upload({ onUpload }) {
  const fileInputRef = useRef();

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onUpload(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      onUpload(e.target.files[0]);
    }
  };

  return (
    <div className="bg-white p-6 rounded shadow-sm">
      <h2 className="text-xl font-bold mb-4">Upload Portrait</h2>
      <div 
        className="border-2 border-dashed border-blue-400 bg-blue-50 rounded-lg p-8 text-center cursor-pointer hover:bg-blue-100 transition"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current.click()}
      >
        <div className="text-blue-500 mb-2">
          <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path>
          </svg>
        </div>
        <p className="text-sm font-medium text-gray-700">Click or drag image to upload</p>
        <p className="text-xs text-gray-500 mt-1">PNG, JPG up to 10MB</p>
        <input 
          type="file" 
          className="hidden" 
          ref={fileInputRef} 
          onChange={handleChange}
          accept="image/*"
        />
      </div>
    </div>
  );
}

export default Upload;
