import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Brush, ResponsiveContainer, ReferenceArea } from 'recharts';
import AdherenceDashboard from './adherencedashboard';

const ZONE_COLORS = {
  "Peak": "rgba(255, 77, 77, 0.2)",
  "Cardio": "rgba(255, 128, 0, 0.2)",
  "Fat Burn": "rgba(255, 204, 0, 0.2)",
  "Out of Range": "rgba(102, 153, 255, 0.1)"
};

function App() {
  // --- STATE MANAGEMENT FOR BOTH VIEWS ---
  const [participants, setParticipants] = useState([]);
  const [selectedParticipant, setSelectedParticipant] = useState(null);
  
  // State for the plot generator controls
  const [startDate, setStartDate] = useState('2024-01-01T00:00');
  const [endDate, setEndDate] = useState('2024-01-02T00:00');
  const [selectedMetric, setSelectedMetric] = useState('intraday_heart_rate');
  const [plots, setPlots] = useState([]);
  const [adherenceReport, setAdherenceReport] = useState(null);

  // All available metrics for the dropdown
  const metricOptions = [
    'intraday_heart_rate',
    'intraday_spo2',
    // 'intraday_breath_rate',
    // 'intraday_active_zone_minute',
    // 'intraday_hrv',
    'intraday_activity',
    'breathing_rate_light',
    'breathing_rate_full',
    'breathing_rate_rem',  
    'breathing_rate_deep',
    'azm_fat_burn',
    'azm_cardio',
    'azm_peak',
    'azm_total',
    'hrv_hf',               
    'hrv_rmssd',            
    'hrv_lf',    
    'hrv_coverage' 
  ];

  // --- DATA FETCHING ---

  // 1. Fetch all participants on initial app load
  useEffect(() => {
    fetch('http://localhost:8000/users')
      .then(res => res.json())
      .then(data => setParticipants(data))
      .catch(error => console.error("Failed to fetch users:", error));

    fetch('http://localhost:8000/adherence')
        .then(res => res.json())
        .then(data => setAdherenceReport(data))
        .catch(error => console.error("Failed to fetch adherence report:", error));
}, []);
  
  // 2. Function to fetch plot data
  const fetchData = (plotKey, metric, page = 1) => {
    if (!selectedParticipant) return;

    const apiUrl = `http://localhost:8000/data?start_date=${startDate}&end_date=${endDate}&user_ids=${selectedParticipant.user_id}&metric=${metric}&page=${page}`;

    if (metric === 'intraday_heart_rate') {
      const zonesApiUrl = `http://localhost:8000/zones?date=${startDate}&user_id=${selectedParticipant.user_id}`;
      Promise.all([
        fetch(apiUrl).then(response => response.json()), 
        fetch(zonesApiUrl).then(response => response.json())
      ])
        .then(([dataResponse, zonesResponse]) => {
          setPlots(prevPlots => {
            const plotIndex = prevPlots.findIndex(p => p.key === plotKey);
            if (plotIndex > -1) {
              // If plot exists, append new data and update page info
              const updatedPlots = [...prevPlots];
              updatedPlots[plotIndex] = {
                ...updatedPlots[plotIndex],
                // data: [...updatedPlots[plotIndex].data, ...responseJson.data],
                data: [...updatedPlots[plotIndex].data, ...dataResponse.data], // assuming backend sends { data: [...] }
                zones: zonesResponse, // Use dynamically fetched zones e.g., { "Peak": {min: 169, max: 220}, ... }
                // page: responseJson.page,
                // hasMore: responseJson.has_more,
                // Save the specific user IDs used for this plot
                queriedUserIds: selectedParticipant.user_id,
                page: dataResponse.page,
                hasMore: dataResponse.has_more,
              };
              return updatedPlots;
            } else {
              // If it's a new plot, add it to the list
              return [...prevPlots, {
                metric: metric,
                // data: responseJson.data,
                // page: responseJson.page,
                // hasMore: responseJson.has_more,
                data: dataResponse.data,
                zones: zonesResponse,
                queriedUserIds: selectedParticipant.user_id,
                page: dataResponse.page,
                hasMore: dataResponse.has_more,
                key: plotKey,
              }];
            }
          });
        })


      .catch(error => console.error('Error fetching data:', error));
    } else {


      console.log(`Fetching data for ${selectedMetric} from: ${apiUrl}`);

      fetch(apiUrl)
        .then(response => response.json())
        .then(responseJson => {
          setPlots(prevPlots => {
            const plotIndex = prevPlots.findIndex(p => p.key === plotKey);
            if (plotIndex > -1) {
              // If plot exists, append new data and update page info
              const updatedPlots = [...prevPlots];
              updatedPlots[plotIndex] = {
                ...updatedPlots[plotIndex],
                data: [...updatedPlots[plotIndex].data, ...responseJson.data],
                page: responseJson.page,
                queriedUserIds: selectedParticipant.user_id,
                hasMore: responseJson.has_more,
              };
              return updatedPlots;
            } else {
              // If it's a new plot, add it to the list
              return [...prevPlots, {
                metric: metric,
                data: responseJson.data,
                page: responseJson.page,
                queriedUserIds: selectedParticipant.user_id,
                hasMore: responseJson.has_more,
                key: plotKey,
              }];
            }
          });
        })
        .catch(error => console.error('Error fetching data:', error));
      }
  };

  const handleAddPlot = () => {
    const plotKey = `${selectedMetric}-${selectedParticipant.user_id}-${new Date().getTime()}`;
    fetchData(plotKey, selectedMetric, 1);
  };
  
  const handleLoadMore = (plotKey, metric, currentPage) => {
    fetchData(plotKey, metric, currentPage + 1);
  };

  const handleParticipantSelect = (participant) => {
    setSelectedParticipant(participant);
    setPlots([]); // Clear plots when switching participants
  };

  // --- STYLING (for layout) ---
  const appStyles = { display: 'flex', fontFamily: 'sans-serif', height: '100vh', overflow: 'hidden' };
  const sidebarStyles = { width: '250px', padding: '20px', borderRight: '1px solid #ccc', background: '#f7f7f7', overflowY: 'auto' };
  const mainContentStyles = { flex: 1, padding: '20px', overflowY: 'auto' };
  const participantListItemStyles = { padding: '10px', cursor: 'pointer', borderRadius: '4px', marginBottom: '5px' };

  // --- UI RENDERING ---
  return (
    <div style={appStyles}>
      <div style={sidebarStyles}>
        <h2>Participants</h2>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {participants.map(p => (
            <li 
              key={p.user_id} 
              style={{...participantListItemStyles, backgroundColor: selectedParticipant?.user_id === p.user_id ? '#e0e0e0' : 'transparent'}}
              onClick={() => handleParticipantSelect(p)}
            >
              {p.name} (ID: {p.user_id})
            </li>
          ))}
        </ul>
      </div>

      <div style={mainContentStyles}>
        {selectedParticipant ? (
          <>
            <h1>Dashboard for {selectedParticipant.name}</h1>
            <p>Use the controls below to add plots to the dashboard.</p>
            <div style={{ marginBottom: '20px', display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap', padding: '10px', border: '1px solid #ddd', borderRadius: '5px' }}>
              <div><label>Start Date: </label><input type="datetime-local" value={startDate} onChange={e => setStartDate(e.target.value)} /></div>
              <div><label>End Date: </label><input type="datetime-local" value={endDate} onChange={e => setEndDate(e.target.value)} /></div>
              <div>
                <label>Metric: </label>
                <select value={selectedMetric} onChange={e => setSelectedMetric(e.target.value)}>
                  {metricOptions.map(option => <option key={option} value={option}>{option}</option>)}
                </select>
              </div>
              <button onClick={handleAddPlot}>Add Plot</button>
              <button onClick={() => setPlots([])}>Clear Plots</button>
            </div>

            {plots.map(plot => (
              <div key={plot.key} style={{ marginBottom: '30px' }}>
                <h2>{plot.metric}</h2>
                {plot.data.length > 0 ? (
                  <>
                <ResponsiveContainer width="95%" height={400}>
                  <LineChart data={plot.data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" tickFormatter={(time) => new Date(time).toLocaleTimeString()} />
                    <YAxis domain={plot.metric === 'intraday_heart_rate' ? [30, 230] : ['dataMin - 5', 'dataMax + 5']} />
                    <Tooltip labelFormatter={(label) => new Date(label).toLocaleString()} />
                    <Legend />

                    {plot.metric === 'intraday_heart_rate' && plot.zones && 
                    Object.entries(plot.zones).map(([zoneName, zoneValues]) => (
                      <ReferenceArea 
                      key={zoneName} 
                      y1={zoneValues.min} 
                      y2={zoneValues.max} 
                      label={zoneName} 
                      fill={ZONE_COLORS[zoneName] || 'rgba(128,128,128,0.2)'}
                      strokeOpacity={0.3} />
                    ))}
                    <Line type="monotone" dataKey="value" name={plot.metric} stroke="#6a1b9a" dot={false} strokeWidth={2} />
                    <Brush dataKey="time" height={30} stroke="#8884d8" />
                  </LineChart>
                </ResponsiveContainer>
                {plot.hasMore && (
                <button onClick={() => handleLoadMore(plot.key, plot.metric, plot.page)} style={{ marginTop: '10px' }}>Load More</button>)}
                </>
                ) : <p>No data found for this selection.</p>}
              </div>
            ))}
            
            <hr style={{ margin: '40px 0' }} />
            <AdherenceDashboard 
                participantReport={selectedParticipant && adherenceReport ? adherenceReport[selectedParticipant.user_id] : null}
            />

          </>
        ) : (
          <h1>Please select a participant to view their dashboard</h1>
        )}
      </div>
    </div>
  );
}

export default App;