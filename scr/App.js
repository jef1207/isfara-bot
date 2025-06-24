// src/App.js
import React, { useState, useEffect } from 'react';
import MasterList from './components/MasterList';
import Calendar from './components/Calendar';
import BookingForm from './components/BookingForm';
import Payment from './components/Payment';

function App() {
  const [step, setStep] = useState(1); // 1 - выбор мастера, 2 - выбор времени, 3 - данные, 4 - оплата
  const [selectedMaster, setSelectedMaster] = useState(null);
  const [selectedTime, setSelectedTime] = useState(null);
  const [bookingData, setBookingData] = useState({});
  const [masters, setMasters] = useState([]);
  
  // Загрузка данных мастеров (в реальном приложении - с бэкенда)
  useEffect(() => {
    // Пример данных
    const mockMasters = [
      { id: 1, name: "Мария Иванова", specialty: "Женские стрижки", rating: 4.9 },
      { id: 2, name: "Игорь Петров", specialty: "Мужские стрижки", rating: 4.8 },
      { id: 3, name: "Анна Сидорова", specialty: "Окрашивание", rating: 5.0 }
    ];
    setMasters(mockMasters);
  }, []);

  const handleSelectMaster = (master) => {
    setSelectedMaster(master);
    setStep(2);
  };

  const handleSelectTime = (time) => {
    setSelectedTime(time);
    setStep(3);
  };

  const handleSubmitForm = (data) => {
    setBookingData({...data, master: selectedMaster, time: selectedTime});
    setStep(4);
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold text-center mb-8">Онлайн запись в парикмахерскую</h1>
      
      {step === 1 && (
        <MasterList masters={masters} onSelect={handleSelectMaster} />
      )}
      
      {step === 2 && selectedMaster && (
        <Calendar master={selectedMaster} onSelectTime={handleSelectTime} />
      )}
      
      {step === 3 && selectedMaster && selectedTime && (
        <BookingForm onSubmit={handleSubmitForm} />
      )}
      
      {step === 4 && (
        <Payment booking={bookingData} />
      )}
    </div>
  );
}

export default App;
