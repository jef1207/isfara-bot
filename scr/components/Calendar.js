// src/components/Calendar.js
import React, { useState } from 'react';
import DatePicker from 'react-datepicker';
import "react-datepicker/dist/react-datepicker.css";

const Calendar = ({ master, onSelectTime }) => {
  const [date, setDate] = useState(new Date());
  const [selectedSlot, setSelectedSlot] = useState(null);
  
  // Генерация временных слотов (в реальном приложении - с бэкенда)
  const timeSlots = [
    '09:00', '10:00', '11:00', '12:00', 
    '13:00', '14:00', '15:00', '16:00', '17:00'
  ];
  
  const handleBooking = (time) => {
    setSelectedSlot(time);
  };
  
  const confirmSelection = () => {
    if (selectedSlot) {
      onSelectTime(`${date.toLocaleDateString()} ${selectedSlot}`);
    }
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-2">
        Выбран мастер: <span className="text-blue-600">{master.name}</span>
      </h2>
      
      <div className="mb-4">
        <label className="block mb-1">Выберите дату:</label>
        <DatePicker
          selected={date}
          onChange={d => setDate(d)}
          minDate={new Date()}
          className="border rounded p-2"
        />
      </div>
      
      <h3 className="font-medium mb-2">Доступное время:</h3>
      <div className="grid grid-cols-4 gap-2">
        {timeSlots.map((time, index) => (
          <button
            key={index}
            className={`py-2 px-3 rounded border ${
              selectedSlot === time 
                ? 'bg-blue-500 text-white' 
                : 'bg-white hover:bg-gray-100'
            }`}
            onClick={() => handleBooking(time)}
          >
            {time}
          </button>
        ))}
      </div>
      
      {selectedSlot && (
        <div className="mt-6">
          <button
            className="bg-green-600 text-white py-2 px-6 rounded hover:bg-green-700"
            onClick={confirmSelection}
          >
            Подтвердить время: {selectedSlot}
          </button>
        </div>
      )}
    </div>
  );
};

export default Calendar;
