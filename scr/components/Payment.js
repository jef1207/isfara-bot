// src/components/Payment.js
import React, { useState } from 'react';

const Payment = ({ booking }) => {
  const [paymentMethod, setPaymentMethod] = useState('card');
  const [isPaid, setIsPaid] = useState(false);
  
  const handlePayment = () => {
    // Здесь будет интеграция с платежным шлюзом
    // В демо-версии просто симулируем успешную оплату
    setTimeout(() => setIsPaid(true), 1500);
  };

  if (isPaid) {
    return (
      <div className="text-center py-8">
        <div className="text-5xl text-green-500 mb-4">✓</div>
        <h2 className="text-2xl font-bold mb-2">Оплата прошла успешно!</h2>
        <p className="mb-4">Ваша бронь подтверждена.</p>
        <div className="bg-gray-100 p-4 rounded-lg max-w-md mx-auto">
          <p><strong>Мастер:</strong> {booking.master.name}</p>
          <p><strong>Время:</strong> {booking.time}</p>
          <p><strong>Имя:</strong> {booking.name}</p>
          <p><strong>Телефон:</strong> {booking.phone}</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Оплата бронирования</h2>
      <div className="bg-gray-100 p-4 rounded-lg mb-6 max-w-md">
        <p><strong>Услуга:</strong> Бронирование времени</p>
        <p><strong>Мастер:</strong> {booking.master.name}</p>
        <p><strong>Дата и время:</strong> {booking.time}</p>
        <p className="text-xl mt-2"><strong>Сумма:</strong> 20 руб.</p>
      </div>
      
      <div className="mb-4">
        <label className="block mb-2">Способ оплаты:</label>
        <div className="flex gap-4">
          <label className="flex items-center">
            <input
              type="radio"
              name="payment"
              checked={paymentMethod === 'card'}
              onChange={() => setPaymentMethod('card')}
              className="mr-2"
            />
            Банковская карта
          </label>
          <label className="flex items-center">
            <input
              type="radio"
              name="payment"
              checked={paymentMethod === 'online'}
              onChange={() => setPaymentMethod('online')}
              className="mr-2"
            />
            Онлайн-кошелек
          </label>
        </div>
      </div>
      
      {paymentMethod === 'card' && (
        <div className="border p-4 rounded-lg max-w-md mb-6">
          <div className="mb-4">
            <label className="block mb-1">Номер карты:</label>
            <input
              type="text"
              placeholder="0000 0000 0000 0000"
              className="w-full p-2 border rounded"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block mb-1">Срок действия:</label>
              <input
                type="text"
                placeholder="ММ/ГГ"
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block mb-1">CVV:</label>
              <input
                type="text"
                placeholder="123"
                className="w-full p-2 border rounded"
              />
            </div>
          </div>
        </div>
      )}
      
      <button
        onClick={handlePayment}
        className="bg-green-600 text-white py-3 px-8 rounded-lg hover:bg-green-700"
      >
        Оплатить 20 руб.
      </button>
    </div>
  );
};

export default Payment;
