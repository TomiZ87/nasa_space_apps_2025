exports.handler = async (event) => {
  console.log('Received event:', JSON.stringify(event, null, 2));

  // Dummy air quality data
  const dummyData = {
    city: 'San Francisco',
    aqi: 42,
    status: 'Good',
    timestamp: new Date().toISOString(),
  };

  return {
    statusCode: 200,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(dummyData),
  };
};
