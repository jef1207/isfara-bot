// src/components/MasterList.js
import React from 'react';

const MasterList = ({ masters, onSelect }) => {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Выберите мастера:</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {masters.map(master => (
          <div 
            key={master.id} 
            className="border rounded-lg p-4 cursor-pointer hover:bg-gray-50 transition"
            onClick={() => onSelect(master)}
          >
            <div className="bg-gray-200 border-2 border-dashed rounded-xl w-16 h-16 mb-2" />
            <h3 className="font-medium">{master.name}</h3>
            <p className="text-sm text-gray-600">{master.specialty}</p>
            <div className="mt-2 flex items-center">
              <span className="text-yellow-500">★</span>
              <span className="ml-1">{master.rating}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MasterList;
