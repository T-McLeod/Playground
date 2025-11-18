// Analytics Dashboard JavaScript

let pieChart = null;
let barChart = null;
let analyticsData = null;

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', () => {
    loadAnalyticsReport();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Regenerate button
    const regenerateBtn = document.getElementById('regenerate-button');
    if (regenerateBtn) {
        regenerateBtn.addEventListener('click', regenerateReport);
    }

    // Retry button
    const retryBtn = document.getElementById('retry-button');
    if (retryBtn) {
        retryBtn.addEventListener('click', loadAnalyticsReport);
    }

    // Modal close buttons
    const modalCloseBtns = document.querySelectorAll('.modal-close, .modal-close-btn');
    modalCloseBtns.forEach(btn => {
        btn.addEventListener('click', closeModal);
    });

    // Close modal when clicking outside
    const modal = document.getElementById('sample-queries-modal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });
    }
}

// Load analytics report from API
async function loadAnalyticsReport() {
    const loadingState = document.getElementById('loading-state');
    const errorState = document.getElementById('error-state');
    const dashboardContent = document.getElementById('dashboard-content');

    // Show loading
    loadingState.style.display = 'block';
    errorState.style.display = 'none';
    dashboardContent.style.display = 'none';

    try {
        const response = await fetch(`/api/analytics/${APP_COURSE_ID}`);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to load analytics report');
        }

        analyticsData = await response.json();

        // Hide loading, show content
        loadingState.style.display = 'none';
        dashboardContent.style.display = 'block';

        // Render the dashboard
        renderDashboard(analyticsData);

    } catch (error) {
        console.error('Failed to load analytics:', error);

        // Show error state
        loadingState.style.display = 'none';
        errorState.style.display = 'block';
        document.getElementById('error-message').textContent = error.message;
    }
}

// Regenerate analytics report
async function regenerateReport() {
    const regenerateBtn = document.getElementById('regenerate-button');
    const originalText = regenerateBtn.innerHTML;

    // Disable button and show loading
    regenerateBtn.disabled = true;
    regenerateBtn.innerHTML = '<span class="spinner-small"></span> Generating...';

    try {
        const response = await fetch('/api/analytics/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                course_id: APP_COURSE_ID
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to regenerate report');
        }


        // Show success message
        alert('Analytics report regenerated successfully!');

        // Reload the report
        await loadAnalyticsReport();

    } catch (error) {
        console.error('Failed to regenerate report:', error);
        alert('Failed to regenerate report: ' + error.message);
    } finally {
        // Re-enable button
        regenerateBtn.disabled = false;
        regenerateBtn.innerHTML = originalText;
    }
}

// Render the dashboard with analytics data
function renderDashboard(data) {
    // Update summary stats
    document.getElementById('total-queries').textContent = data.total_queries || 0;
    document.getElementById('total-topics').textContent = data.num_clusters || 0;
    document.getElementById('auto-detected').textContent = data.auto_detected ? 'Yes' : 'No';

    // Format and display report date
    if (data.generated_at) {
        const date = new Date(data.generated_at);
        document.getElementById('report-date').textContent = date.toLocaleDateString();
    }

    // Convert clusters object to array format - GET ALL CLUSTERS
    const allClusters = convertClustersToArray(data.clusters || {});

    // Render charts with all clusters
    renderCharts(allClusters);

    // Render topic details with all clusters
    renderTopicDetails(allClusters);
}

// Convert clusters object to array format
function convertClustersToArray(clustersObj) {
    const clustersArray = [];
    
    for (const [label, info] of Object.entries(clustersObj)) {
        clustersArray.push({
            label: label,
            query_count: info.count || 0,
            sample_queries: info.sample_queries || [],
            ratings: info.ratings || { good: 0, bad: 0, none: 0 }
        });
    }
    
    // Sort by count (descending)
    clustersArray.sort((a, b) => b.query_count - a.query_count);
    
    // Return ALL clusters (not just top 5)
    return clustersArray;
}

// Render pie and bar charts
function renderCharts(clusters) {
    // Prepare data for PIE CHART - show ALL topics
    const allLabels = clusters.map(cluster => cluster.label || 'Unknown Topic');
    const allCounts = clusters.map(cluster => cluster.query_count || 0);
    const allColors = generateColors(clusters.length);

    // Prepare data for BAR CHART - show top 5 only
    const top5Clusters = clusters.slice(0, 5);
    const top5Labels = top5Clusters.map(cluster => cluster.label || 'Unknown Topic');
    const top5Colors = generateColors(top5Clusters.length);

    // Destroy existing charts if they exist
    if (pieChart) {
        pieChart.destroy();
    }
    if (barChart) {
        barChart.destroy();
    }

    // Pie Chart - ALL TOPICS
    const pieCtx = document.getElementById('topic-pie-chart').getContext('2d');
    pieChart = new Chart(pieCtx, {
        type: 'pie',
        data: {
            labels: allLabels,
            datasets: [{
                data: allCounts,
                backgroundColor: allColors,
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} queries (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });

    // Bar Chart (Stacked) - TOP 5 ONLY
    const barCtx = document.getElementById('topic-bar-chart').getContext('2d');
    barChart = new Chart(barCtx, {
        type: 'bar',
        data: {
            labels: top5Labels,
            datasets: [
                {
                    label: 'Not Helpful',
                    data: top5Clusters.map(c => c.ratings.bad),
                    backgroundColor: '#F44336', // Red
                    borderColor: '#D32F2F',
                    borderWidth: 1
                },
                {
                    label: 'Helpful',
                    data: top5Clusters.map(c => c.ratings.good),
                    backgroundColor: '#4CAF50', // Green
                    borderColor: '#388E3C',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                x: {
                    stacked: true,
                    ticks: {
                        font: {
                            size: 11
                        }
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    },
                    title: {
                        display: true,
                        text: 'Number of Queries'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        padding: 10,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return context[0].label;
                        },
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y || 0;
                            return `${label}: ${value} queries`;
                        },
                        footer: function(context) {
                            // Calculate total for this bar
                            const index = context[0].dataIndex;
                            const total = top5Clusters[index].query_count;
                            return `Total: ${total} queries`;
                        }
                    }
                },
                title: {
                    display: true,
                    text: 'Top 5 Topics by Query Volume & Quality',
                    font: {
                        size: 14,
                        weight: 'bold'
                    },
                    padding: {
                        bottom: 10
                    }
                }
            }
        }
    });
}

// Render topic details list
function renderTopicDetails(clusters) {
    const detailsList = document.getElementById('topic-details-list');
    detailsList.innerHTML = '';

    clusters.forEach((cluster, index) => {
        const detailCard = document.createElement('div');
        detailCard.className = 'topic-detail-card';

        const header = document.createElement('div');
        header.className = 'topic-detail-header';

        const title = document.createElement('h3');
        title.textContent = cluster.label || 'Unknown Topic';

        const count = document.createElement('span');
        count.className = 'topic-count';
        count.textContent = `${cluster.query_count || 0} queries`;

        header.appendChild(title);
        header.appendChild(count);

        // Add ratings breakdown
        const ratingsDiv = document.createElement('div');
        ratingsDiv.className = 'ratings-breakdown';
        
        const goodPercent = cluster.query_count > 0 
            ? ((cluster.ratings.good / cluster.query_count) * 100).toFixed(1) 
            : 0;
        const badPercent = cluster.query_count > 0 
            ? ((cluster.ratings.bad / cluster.query_count) * 100).toFixed(1) 
            : 0;
        const nonePercent = cluster.query_count > 0 
            ? ((cluster.ratings.none / cluster.query_count) * 100).toFixed(1) 
            : 0;

        ratingsDiv.innerHTML = `
            <span class="rating-stat rating-good">👍 ${cluster.ratings.good} (${goodPercent}%)</span>
            <span class="rating-stat rating-bad">👎 ${cluster.ratings.bad} (${badPercent}%)</span>
            <span class="rating-stat rating-none">⚪ ${cluster.ratings.none} (${nonePercent}%)</span>
        `;

        const moreInfoBtn = document.createElement('button');
        moreInfoBtn.className = 'btn-secondary more-info-btn';
        moreInfoBtn.textContent = 'View Sample Queries';
        moreInfoBtn.addEventListener('click', () => showSampleQueries(cluster));

        detailCard.appendChild(header);
        detailCard.appendChild(ratingsDiv);
        detailCard.appendChild(moreInfoBtn);

        detailsList.appendChild(detailCard);
    });
}

// Show sample queries modal
function showSampleQueries(cluster) {
    const modal = document.getElementById('sample-queries-modal');
    const modalTitle = document.getElementById('modal-topic-name');
    const modalQueries = document.getElementById('modal-sample-queries');

    // Populate modal
    modalTitle.textContent = cluster.label || 'Unknown Topic';

    // Clear and populate sample queries
    modalQueries.innerHTML = '';
    const samples = cluster.sample_queries || [];

    if (samples.length === 0) {
        const li = document.createElement('li');
        li.textContent = 'No sample queries available';
        li.style.fontStyle = 'italic';
        modalQueries.appendChild(li);
    } else {
        samples.forEach(query => {
            const li = document.createElement('li');
            li.textContent = query;
            modalQueries.appendChild(li);
        });
    }

    // Show modal
    modal.style.display = 'flex';
}

// Close modal
function closeModal() {
    const modal = document.getElementById('sample-queries-modal');
    modal.style.display = 'none';
}

// Generate distinct colors for charts
function generateColors(count) {
    const baseColors = [
        '#FF6384', // Coral Pink
        '#36A2EB', // Sky Blue
        '#FFCE56', // Sunny Yellow
        '#4BC0C0', // Turquoise
        '#9966FF', // Purple
        '#FF9F40', // Orange
        '#FF6B9D', // Hot Pink
        '#95E1D3', // Mint Green
        '#F38181', // Salmon
        '#AA96DA', // Lavender
        '#FCBAD3', // Light Pink
        '#A8E6CF', // Seafoam Green
        '#FFD3B6', // Peach
        '#FFAAA5', // Coral
        '#FF8B94', // Rose
        '#A2D2FF', // Powder Blue
        '#BDB2FF', // Periwinkle
        '#FFC6FF', // Orchid
        '#FDFFB6', // Lemon
        '#CAFFBF', // Pistachio
        '#9BF6FF', // Cyan
        '#FEC89A', // Apricot
        '#F9DCC4'  // Cream
    ];

    const colors = [];
    for (let i = 0; i < count; i++) {
        colors.push(baseColors[i % baseColors.length]);
    }

    return colors;
}

// Darken a color for borders
function darkenColor(color) {
    // Simple darkening by reducing RGB values
    const hex = color.replace('#', '');
    const r = Math.max(0, parseInt(hex.substring(0, 2), 16) - 30);
    const g = Math.max(0, parseInt(hex.substring(2, 4), 16) - 30);
    const b = Math.max(0, parseInt(hex.substring(4, 6), 16) - 30);

    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}
