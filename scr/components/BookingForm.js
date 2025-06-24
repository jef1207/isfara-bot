// src/components/BookingForm.js
import React, { useState } from 'react';

const BookingForm = ({ onSubmit }) => {
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    comment: ''
  });
  
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };
  
  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Ваши контактные данные</h2>
      <form onSubmit={handleSubmit} className="max-w-md">
        <div className="mb-4">
          <label className="block mb-1">Имя:</label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
            className="w-full p-2 border rounded"
          />
        </div>
        
        <div className="mb-4">
          <label className="block mb-1">Телефон:</label>
          <input
            type="tel"
            name="phone"
            value={formData.phone}
            onChange={handleChange}
            required
            className="w-full p-2 border rounded"
          />
        </div>
        
        <div className="mb-4">
          <label className="block mb-1">Email:</label>
          <input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
            className="w-full p-2 border rounded"
          />
        </div>
        
        <div className="mb-4">
          <label className="block mb-1">Комментарий:</label>
          <textarea
            name="comment"
            value={formData.comment}
            onChange={handleChange}
            className="w-full p-2 border rounded"
            rows="3"
          />
        </div>
        
        <button
          type="submit"
          className="bg-blue-600 text-white py-2 px-6 rounded hover:bg-blue-700"
        >
          Перейти к оплате
        </button>
      </form>
    </div>
  );
};

export default BookingForm;
