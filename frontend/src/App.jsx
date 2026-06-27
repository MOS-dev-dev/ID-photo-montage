import React, { useState } from 'react';
import Upload from './Upload';
import CanvasEditor from './CanvasEditor';
import Controls from './Controls';
import AutoMode from './AutoMode';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

function App() {
  const [appMode, setAppMode] = useState('auto'); // 'auto' or 'manual'
  const [imageId, setImageId] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [outputUrl, setOutputUrl] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  
  const [frameConfig, setFrameConfig] = useState({
    x: 0,
    y: 0,
    scale: 0.75,
    rotation: 0,
    width: 0,
    height: 0,
    canvas_width: 490,
    canvas_height: 650
  });

  React.useEffect(() => {
    // Load saved frame on mount
    axios.get(`${API_BASE}/frame`).then(res => {
      if (res.data) {
        setFrameConfig(prev => ({ ...prev, ...res.data }));
      }
    }).catch(e => console.error("Could not load frame on mount", e));
  }, []);

  const [imageAdjust, setImageAdjust] = useState({
    brightness: 1.0,
    contrast: 1.0,
    saturation: 1.0
  });

  const [errorMsg, setErrorMsg] = useState(null);

  const [isEditingFrame, setIsEditingFrame] = useState(false);

  // We need generateCard to be callable with params so we can call it right after upload
  const doGenerateCard = async (imgId, frame, adjust, file) => {
    setIsGenerating(true);
    setErrorMsg(null);
    try {
      console.log("FRAME SENT", frame);
      const formData = new FormData();
      if (file) {
        formData.append('image', file);
      }
      formData.append('id', imgId);
      formData.append('frame_json', JSON.stringify(frame));
      formData.append('image_adjust', JSON.stringify(adjust));
      formData.append('text_data', JSON.stringify({
        id_num: "0123456789",
        last_name: "NGUYEN",
        first_name: "VAN A",
        middle_name: "THI",
        dob: "01/01/1990",
        address: "123 Street, City"
      }));

      const res = await axios.post(`${API_BASE}/generate`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setOutputUrl(res.data.output_url);
    } catch (e) {
      console.error(e);
      if (e.message === 'Network Error') {
        setErrorMsg('Backend not running');
      } else {
        setErrorMsg('Processing failed');
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleUpload = async (file) => {
    setErrorMsg(null);
    setSelectedFile(file);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await axios.post(`${API_BASE}/upload`, formData);
      const newId = res.data.id;
      setImageId(newId);
      setPreviewUrl(res.data.preview_url);
      
      // Automatic generation
      await doGenerateCard(newId, frameConfig, imageAdjust, file);
      setIsEditingFrame(false); // Make sure we show the generated card
    } catch (e) {
      console.error(e);
      if (e.message === 'Network Error') {
        setErrorMsg('Backend not running');
      } else {
        setErrorMsg('Processing failed');
      }
    }
  };

  const generateCard = () => {
    if (!imageId) return;
    doGenerateCard(imageId, frameConfig, imageAdjust, selectedFile);
    setIsEditingFrame(false);
  };

  const handleSaveFrame = async () => {

    try {
      await axios.post(`${API_BASE}/save_frame`, { frame: frameConfig });
      alert('Frame saved successfully to frame.json!');
    } catch (e) {
      console.error(e);
      alert('Save frame failed');
    }
  };

  const handleResetPosition = () => {
    // We will pass this to CanvasEditor to reset the image
    setFrameConfig(prev => ({ ...prev, reset: Date.now() }));
  };

  return (
    <div className="min-h-screen p-8 bg-gray-50">
      <h1 className="text-3xl font-bold text-gray-800 mb-4 text-center">ID Card Generator</h1>
      
      <div className="flex justify-center mb-8">
        <div className="inline-flex bg-gray-200 rounded-lg p-1">
          <button 
            onClick={() => setAppMode('auto')}
            className={`px-6 py-2 rounded-md font-semibold ${appMode === 'auto' ? 'bg-white shadow text-blue-600' : 'text-gray-600 hover:text-gray-800'}`}
          >
            Auto Mode
          </button>
          <button 
            onClick={() => setAppMode('manual')}
            className={`px-6 py-2 rounded-md font-semibold ${appMode === 'manual' ? 'bg-white shadow text-blue-600' : 'text-gray-600 hover:text-gray-800'}`}
          >
            Manual Editor
          </button>
        </div>
      </div>
      
      {errorMsg && (
        <div className="max-w-7xl mx-auto mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative">
          <span className="block sm:inline">{errorMsg}</span>
        </div>
      )}

      {appMode === 'auto' ? (
        <AutoMode />
      ) : (
        <div className="grid grid-cols-12 gap-6 max-w-7xl mx-auto">
        {/* Left: Upload */}
        <div className="col-span-3">
          <Upload onUpload={handleUpload} />
        </div>
        
        {/* Center: Canvas / Preview */}
        <div className="col-span-6 bg-white p-4 rounded shadow-sm flex flex-col items-center">
          <div className="w-full flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">
              {isEditingFrame ? "Edit Frame" : "Real Card Preview"}
            </h2>
            {imageId && (
              <button 
                onClick={() => setIsEditingFrame(!isEditingFrame)}
                className="bg-purple-100 hover:bg-purple-200 text-purple-800 px-3 py-1 rounded text-sm font-semibold"
              >
                {isEditingFrame ? "View Final Card" : "Adjust Frame"}
              </button>
            )}
          </div>

          {isEditingFrame && previewUrl ? (
            <CanvasEditor 
              imageUrl={previewUrl} 
              frameConfig={frameConfig}
              onFrameChange={setFrameConfig}
            />
          ) : outputUrl ? (
            <div className="flex flex-col items-center">
              <img src={outputUrl} alt="Final Card" className="max-w-full border-2 border-gray-300 rounded shadow-md" style={{width: 490, height: 650}} />
              <a 
                href={outputUrl} 
                download="id_card.png"
                className="mt-4 bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-8 rounded shadow"
              >
                Download Final Card
              </a>
            </div>
          ) : (
            <img src="/template.png" alt="Template" className="max-w-full border-2 border-dashed border-gray-300 rounded opacity-50" style={{width: 490, height: 650}} />
          )}
        </div>
        
        {/* Right: Controls */}
        <div className="col-span-3">
          <Controls 
            frameConfig={frameConfig}
            imageAdjust={imageAdjust}
            onAdjustChange={setImageAdjust}
            onGenerate={generateCard}
            onSaveFrame={handleSaveFrame}
            onResetPosition={handleResetPosition}
            isGenerating={isGenerating}
            disabled={!imageId}
          />
        </div>
        </div>
      )}
    </div>
  );
}

export default App;
