import React from 'react';

// This component now receives the specific user's report data as a "prop"
function AdherenceDashboard({ participantReport }) {

    // If no report data is passed, don't render anything
    if (!participantReport) {
        return null;
    }

    return (
        <div style={{ marginTop: '40px' }}>
            <h2>Participant Adherence Overview</h2>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ borderBottom: '2px solid black' }}>
                        <th style={{ textAlign: 'left', padding: '8px' }}>Name</th>
                        <th style={{ textAlign: 'left', padding: '8px' }}>Status Flags</th>
                        <th style={{ textAlign: 'left', padding: '8px' }}>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {/* The table now only shows the single selected user */}
                    <tr style={{ borderBottom: '1px solid #ccc' }}>
                        <td style={{ padding: '8px' }}>{participantReport.name}</td>
                        <td style={{ padding: '8px' }}>
                            {participantReport.flags.length > 0 ? (
                                <ul style={{ margin: 0, paddingLeft: '20px' }}>
                                    {participantReport.flags.map((flag, index) => (
                                        <li key={index} style={{ color: 'red' }}>{flag}</li>
                                    ))}
                                </ul>
                            ) : (
                                <span style={{ color: 'green' }}>Good Standing</span>
                            )}
                        </td>
                        <td style={{ padding: '8px' }}>
                            {participantReport.flags.length > 0 && (
                                <a href={`mailto:${participantReport.email}?subject=Fitbit Study Adherence`}>
                                    Contact
                                </a>
                            )}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    );
}

export default AdherenceDashboard;