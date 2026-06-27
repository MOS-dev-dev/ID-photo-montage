import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

function AutoMode() {
  const [outputFolder, setOutputFolder] = useState(null);
  const [outputFiles, setOutputFiles] = useState([]);
  const [zipUrl, setZipUrl] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isZip, setIsZip] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0, percent: 0, status: 'idle' });
  
  const [adjustments, setAdjustments] = useState({
    brightness: 1.05,
    contrast: 1.08,
    saturation: 1.10
  });
  const [livePreview, setLivePreview] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  
  const pollingRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      setSelectedFiles(files);
      
      if (files.length === 1 && files[0].name.toLowerCase().endsWith('.zip')) {
        setIsZip(true);
      } else {
        setIsZip(false);
      }
      
      setOutputFolder(null);
      setOutputFiles([]);
      setZipUrl(null);
      setPreviewUrl(null);
      setProgress({ current: 0, total: 0, percent: 0, status: 'idle' });
    }
  };

  const fetchResults = async (batchId) => {
    try {
      const res = await axios.get(`${API_BASE}/batch_results/${batchId}`);
      setOutputFolder(res.data.output_folder);
      setOutputFiles(res.data.files);
      if (res.data.zip_url) setZipUrl(res.data.zip_url);
    } catch (err) {
      console.error("Failed to fetch batch results", err);
      setErrorMsg("Failed to load generated images.");
    }
  };

  const startPolling = (batchId) => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    
    pollingRef.current = setInterval(async () => {
      try {
        const res = await axios.get(`${API_BASE}/batch_progress/${batchId}`);
        setProgress(res.data);
        if (res.data.status === 'completed') {
          clearInterval(pollingRef.current);
          fetchResults(batchId);
        } else if (res.data.status === 'error') {
          clearInterval(pollingRef.current);
        }
      } catch (err) {
        console.error("Polling error", err);
      }
    }, 500);
  };

  const handleGenerate = async () => {
    if (selectedFiles.length === 0) {
      setErrorMsg("Please select images or a ZIP file first.");
      return;
    }
    
    setIsGenerating(true);
    setErrorMsg(null);
    setProgress({ current: 0, total: 0, percent: 0, status: 'processing' });
    
    const batchId = Math.random().toString(36).substring(2, 15);
    const formData = new FormData();
    formData.append('batch_id', batchId);
    formData.append('adjustments', JSON.stringify(adjustments));
    
    if (isZip) {
      formData.append('zip_file', selectedFiles[0]);
    } else {
      selectedFiles.forEach(file => {
        formData.append('images', file);
      });
    }
    
    startPolling(batchId);
    
    try {
      await axios.post(`${API_BASE}/batch_generate`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      // Do not set outputs here since the backend is processing in background
    } catch (e) {
      console.error(e);
      if (e.message === 'Network Error') {
        setErrorMsg('Backend not running');
      } else {
        setErrorMsg('Processing failed: ' + (e.response?.data?.detail || e.message));
      }
      setProgress(prev => ({ ...prev, status: 'error' }));
      if (pollingRef.current) clearInterval(pollingRef.current);
      setIsGenerating(false);
    }
  };

  useEffect(() => {
    if (progress.status === 'completed' || progress.status === 'error') {
      setIsGenerating(false);
    }
  }, [progress.status]);

  useEffect(() => {
    if (livePreview && selectedFiles.length > 0 && !isZip) {
      const delayDebounceFn = setTimeout(async () => {
        setIsPreviewing(true);
        const formData = new FormData();
        formData.append('image', selectedFiles[0]);
        formData.append('adjustments', JSON.stringify(adjustments));
        try {
          const res = await axios.post(`${API_BASE}/auto_preview`, formData);
          setPreviewUrl(res.data.preview_url);
        } catch (e) {
          console.error("Preview failed", e);
        } finally {
          setIsPreviewing(false);
        }
      }, 500);

      return () => clearTimeout(delayDebounceFn);
    } else if (!livePreview || isZip) {
      setPreviewUrl(null);
    }
  }, [adjustments, livePreview, selectedFiles, isZip]);

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const percentage = progress.percent || 0;

  return (
    <div className="flex flex-col items-center max-w-5xl mx-auto bg-white p-8 rounded-lg shadow mt-8">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">Auto Mode: Batch Generation</h2>
      
      {errorMsg && (
        <div className="w-full mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {errorMsg}
        </div>
      )}

      <div className="grid grid-cols-2 gap-8 w-full">
        {/* Left Side: Upload & Input */}
        <div className="flex flex-col items-center">
          <div className="w-full h-80 border-2 border-dashed border-gray-300 rounded flex flex-col items-center justify-center overflow-hidden bg-gray-50 mb-4 relative hover:bg-gray-100 transition-colors">
            {selectedFiles.length > 0 ? (
              <div className="text-center p-4">
                <svg className="mx-auto h-16 w-16 mb-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"></path></svg>
                <p className="font-semibold text-gray-700 text-lg">
                  {isZip ? selectedFiles[0].name : `${selectedFiles.length} images selected`}
                </p>
                <p className="text-sm text-gray-500 mt-2">Click or drag to change files</p>
              </div>
            ) : (
              <div className="text-gray-400 text-center p-4">
                <svg className="mx-auto h-16 w-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                <p className="font-semibold text-lg text-gray-600">Drag & Drop Folder / ZIP</p>
                <p className="text-sm mt-1">or click to browse multiple files</p>
              </div>
            )}
            <input 
              type="file" 
              multiple
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" 
              accept="image/*,.zip"
              onChange={handleFileChange}
            />
          </div>
          
          {/* Adjustments Panel */}
          <div className="w-full bg-gray-50 p-4 rounded border border-gray-200 mb-4 shadow-sm">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-bold text-gray-700">Adjustments</h3>
              <label className="flex items-center space-x-2 cursor-pointer text-sm">
                <input 
                  type="checkbox" 
                  checked={livePreview}
                  onChange={(e) => setLivePreview(e.target.checked)}
                  disabled={isZip || selectedFiles.length === 0}
                  className="form-checkbox h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <span className={isZip || selectedFiles.length === 0 ? "text-gray-400" : "text-gray-700"}>Live Preview</span>
              </label>
            </div>
            
            {livePreview && previewUrl && (
               <div className="mb-4 relative rounded overflow-hidden border border-gray-300 bg-white flex justify-center items-center" style={{height: '240px'}}>
                 {isPreviewing && <div className="absolute inset-0 bg-white bg-opacity-70 flex justify-center items-center z-10"><span className="text-gray-600 font-semibold shadow-sm">Updating...</span></div>}
                 <img src={previewUrl} alt="Preview" className="h-full w-auto object-contain" />
               </div>
            )}
            
            <div className="space-y-3 text-sm text-gray-700">
              <div className="flex flex-col">
                <div className="flex justify-between font-semibold">
                  <span>Brightness</span>
                  <span>{adjustments.brightness.toFixed(2)}</span>
                </div>
                <input type="range" min="0.5" max="1.5" step="0.05" 
                       value={adjustments.brightness} 
                       onChange={(e) => setAdjustments({...adjustments, brightness: parseFloat(e.target.value)})} 
                       className="w-full mt-1" />
              </div>
              <div className="flex flex-col">
                <div className="flex justify-between font-semibold">
                  <span>Contrast</span>
                  <span>{adjustments.contrast.toFixed(2)}</span>
                </div>
                <input type="range" min="0.5" max="1.5" step="0.05" 
                       value={adjustments.contrast} 
                       onChange={(e) => setAdjustments({...adjustments, contrast: parseFloat(e.target.value)})} 
                       className="w-full mt-1" />
              </div>
              <div className="flex flex-col">
                <div className="flex justify-between font-semibold">
                  <span>Saturation</span>
                  <span>{adjustments.saturation.toFixed(2)}</span>
                </div>
                <input type="range" min="0.0" max="2.0" step="0.05" 
                       value={adjustments.saturation} 
                       onChange={(e) => setAdjustments({...adjustments, saturation: parseFloat(e.target.value)})} 
                       className="w-full mt-1" />
              </div>
            </div>
          </div>
          
          <button 
            onClick={handleGenerate}
            disabled={isGenerating || selectedFiles.length === 0}
            className={`w-full py-4 px-4 text-white font-bold rounded shadow-lg transition-colors text-lg ${
              isGenerating || selectedFiles.length === 0 
                ? 'bg-blue-300 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {isGenerating ? "Processing Batch..." : "Start Batch Generation"}
          </button>
        </div>

        {/* Right Side: Output & Progress */}
        <div className="flex flex-col items-center">
          <div className="w-full bg-gray-50 rounded flex flex-col items-center p-6 border-2 border-gray-200" style={{ minHeight: '380px' }}>
            
            {(isGenerating || progress.total > 0) && (
              <div className="w-full mb-6">
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-semibold text-gray-700">
                    {progress.status === 'completed' ? 'Done!' : 'Processing...'}
                  </span>
                  <span className="text-sm font-bold text-blue-600">
                    {progress.current} / {progress.total}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4 shadow-inner">
                  <div 
                    className="bg-blue-600 h-4 rounded-full transition-all duration-500 ease-out" 
                    style={{ width: `${percentage}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-500 mt-2 text-right">{percentage}% Complete</p>
              </div>
            )}

            {outputFolder ? (
              <div className="flex flex-col items-center w-full">
                <div className="bg-green-50 border border-green-200 text-green-800 rounded p-4 mb-4 w-full text-center flex flex-col items-center">
                  <p className="font-bold text-lg mb-1">Batch Completed Successfully!</p>
                  <p className="text-sm text-green-600 break-all text-xs mb-3">{outputFolder}</p>
                  {zipUrl && (
                    <a 
                      href={zipUrl} 
                      download 
                      className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded shadow flex items-center transition-colors"
                    >
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                      Download All (ZIP)
                    </a>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-2 w-full max-h-60 overflow-y-auto p-2 border bg-white rounded shadow-inner">
                  {outputFiles.map((url, idx) => (
                    <div key={idx} className="relative group rounded border overflow-hidden">
                      <img src={url} alt={`Output ${idx}`} className="w-full h-auto object-cover" />
                      <a 
                        href={url}
                        download={`card_${idx+1}.png`}
                        className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <span className="text-white text-sm font-bold bg-blue-500 px-3 py-1 rounded">Download</span>
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              !isGenerating && (
                <div className="text-gray-400 text-center m-auto flex flex-col items-center">
                  <svg className="w-16 h-16 mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                  <p className="text-lg">Results will appear here</p>
                  <p className="text-sm mt-2">Images will be saved to outputs/batch_xxx/</p>
                </div>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AutoMode;
