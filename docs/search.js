// Supabase Configuration
const SUPABASE_URL = 'https://vhgpyvzgmvhijqgsapnk.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZoZ3B5dnpnbXZoaWpxZ3NhcG5rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI4Njc1MjAsImV4cCI6MjA3ODQ0MzUyMH0.Cp4oyw2M72RCFnsKeLg49hSMvGs4pm6-ul0sFmAasRs';

// Supabase client - initialized in DOMContentLoaded
let supabaseClient;

// State
let currentResults = [];
let displayedResults = [];
let currentFilters = {
    category: 'all'
};
let searchTimeout;
let currentPage = 1;
const RESULTS_PER_PAGE = 100;

// Date/Time constants (shared across functions)
const DAYS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];

// Security: Escape HTML to prevent XSS attacks
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Supabase client here to ensure library is loaded
    if (window.supabase && window.supabase.createClient) {
        supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    } else {
        console.error('DOMContentLoaded: window.supabase not available!');
    }

    setupEventListeners();
    checkConnection();
    loadAnalytics();
    loadStatsUpdated();
    checkUrlQuery(); // Check if URL has a search query
    setupRealtimeUpdates(); // Subscribe to database changes
});

// Polling for updates (checks every 5 minutes)
let lastKnownSync = null;
const POLL_INTERVAL = 5 * 60 * 1000; // 5 minutes

function setupRealtimeUpdates() {
    if (!supabaseClient) {
        console.warn('Polling: Supabase client not available');
        return;
    }


    // Get initial last_sync value
    fetchLastSync().then(syncTime => {
        lastKnownSync = syncTime;
    });

    // Check for updates every 5 minutes
    setInterval(async () => {
        const currentSync = await fetchLastSync();
        if (currentSync && lastKnownSync && currentSync !== lastKnownSync) {
            lastKnownSync = currentSync;
            handleRealtimeUpdate();
        }
    }, POLL_INTERVAL);
}

async function fetchLastSync() {
    try {
        const { data, error } = await supabaseClient
            .from('metadata')
            .select('value')
            .eq('key', 'last_sync')
            .single();

        if (error) throw error;
        return data?.value || null;
    } catch (e) {
        console.error('Polling: Error fetching last_sync:', e);
        return null;
    }
}

function handleRealtimeUpdate(payload) {
    // Show notification
    showUpdateNotification();

    // If user is actively searching, auto-refresh results
    const searchInput = document.getElementById('searchInput');
    if (searchInput && searchInput.value.trim().length >= 3) {
        performSearch();
    }

    // Refresh stats
    loadStatsUpdated();
    loadAnalytics();
}

function showUpdateNotification() {
    // Create notification if it doesn't exist
    let notification = document.getElementById('updateNotification');
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'updateNotification';
        notification.className = 'update-notification';
        notification.innerHTML = '🔄 Database updated! Results refreshed.';
        document.body.appendChild(notification);
    }

    // Show notification
    notification.classList.add('show');

    // Hide after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

function setupEventListeners() {
    // Search input with debounce
    document.getElementById('searchInput').addEventListener('input', (e) => {
        // Clear URL immediately when user starts typing
        // updateUrlQuery(''); // Removed: shareable links disabled

        clearTimeout(searchTimeout);

        // If input is cleared, hide results
        if (e.target.value.trim().length === 0) {
            document.getElementById('resultsPanel').style.display = 'none';
            document.getElementById('error').innerHTML = '';
            currentResults = [];
            displayedResults = [];
            return;
        }

        searchTimeout = setTimeout(() => {
            if (e.target.value.trim().length >= 2) {
                performSearch();
            }
        }, 300);
    });

    // Enter key to search
    document.getElementById('searchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    // Filter chips with debounce
    let filterTimeout;
    document.querySelectorAll('.filter-chip').forEach(btn => {
        btn.addEventListener('click', () => {
            const filterType = btn.dataset.filter;
            const filterValue = btn.dataset.value;

            // Update active state
            document.querySelectorAll(`[data-filter="${filterType}"]`).forEach(b => {
                b.classList.remove('active');
            });
            btn.classList.add('active');

            // Update filter
            currentFilters[filterType] = filterValue;

            // Debounced search to prevent rate limiting
            clearTimeout(filterTimeout);
            filterTimeout = setTimeout(() => {
                const query = document.getElementById('searchInput').value.trim();
                if (query.length >= 2) {
                    performSearch();
                }
            }, 300);
        });
    });
}

// Check database connection status
async function checkConnection() {
    const statusEl = document.getElementById('connectionStatus');

    try {
        // statusEl is already set to 'Busy' in static HTML

        // Try a simple query to check connection
        const { data, error } = await supabaseClient
            .from('rx')
            .select('id')
            .limit(1);

        if (error) throw error;

        // Connected successfully
        // Generate current date for display (static)
        const now = new Date();
        const day = now.getDate().toString().padStart(2, '0');
        const month = MONTHS[now.getMonth()];
        const year = now.getFullYear();
        const dateText = `${day} ${month} ${year}`;

        statusEl.className = 'header-status connected';
        statusEl.innerHTML = `<span class="status-dot"></span><span class="status-text">Live</span><span class="status-separator">|</span><span class="status-date" id="lastUpdated">${dateText} <span id="liveTime"></span></span>`;

        // Start the live clock for time portion only
        startLiveClock();

    } catch (error) {
        console.error('Connection error:', error);

        // Get date text again
        const dateEl = document.getElementById('lastUpdated');
        const dateText = dateEl ? dateEl.textContent : 'Loading...';

        statusEl.className = 'header-status error';
        statusEl.innerHTML = `<span class="status-dot"></span><span class="status-text">Offline</span>`;
    }
}

// Live clock - updates time every second (HH:MM:SS)
function startLiveClock() {
    function updateTime() {
        const now = new Date();
        const hours = now.getHours().toString().padStart(2, '0');
        const minutes = now.getMinutes().toString().padStart(2, '0');
        const seconds = now.getSeconds().toString().padStart(2, '0');
        const timeStr = `${hours}:${minutes}:${seconds}`;

        const liveTimeEl = document.getElementById('liveTime');
        if (liveTimeEl) {
            liveTimeEl.textContent = timeStr;
        }
    }

    // Update immediately, then every second
    updateTime();
    setInterval(updateTime, 1000);
}

// Format timestamp for display in IST: "THU 11 DEC 2025 17:31"
function formatUpdatedTimestamp(date) {
    // Force IST timezone using toLocaleString
    const options = {
        timeZone: 'Asia/Kolkata',
        weekday: 'short',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    };

    const formatted = date.toLocaleString('en-IN', options);
    // Convert to uppercase format: "THU 18 DEC 2025 13:15" - remove all commas
    return formatted.toUpperCase().replace(/,/g, '');
}

// Fetch and display the last sync timestamp
async function loadStatsUpdated() {
    const CACHE_KEY = 'tgpc_last_sync';
    const syncTimestampEl = document.getElementById('syncTimestamp');


    if (!syncTimestampEl) {
        return;
    }

    function updateDisplay(dateStr) {
        syncTimestampEl.textContent = dateStr;
    }

    // Try to load from cache first
    const cached = localStorage.getItem(CACHE_KEY);
    if (cached) {
        try {
            // Ensure timestamp is treated as UTC by appending Z if missing
            const utcValue = cached.endsWith('Z') ? cached : cached + 'Z';
            const cachedDate = new Date(utcValue);
            updateDisplay(formatUpdatedTimestamp(cachedDate));
        } catch (e) {
            localStorage.removeItem(CACHE_KEY);
        }
    }

    try {
        // Fetch from Supabase metadata table
        const { data, error } = await supabaseClient
            .from('metadata')
            .select('value')
            .eq('key', 'last_sync')
            .single();


        if (error) {
            console.error('loadStatsUpdated: Supabase error:', error);
        }

        if (!error && data && data.value) {
            // Ensure timestamp is treated as UTC by appending Z if missing
            const utcValue = data.value.endsWith('Z') ? data.value : data.value + 'Z';
            const syncDate = new Date(utcValue);
            updateDisplay(formatUpdatedTimestamp(syncDate));
            localStorage.setItem(CACHE_KEY, utcValue);
        } else {
        }
    } catch (error) {
        console.error('loadStatsUpdated: Exception:', error);
    }
}

// Load analytics - production grade with single RPC call
async function loadAnalytics() {
    const CACHE_KEY = 'tgpc_analytics';

    // Fallback stats (shown instantly)
    const fallbackStats = {
        total: 83103,
        categories: {
            'BPharm': 57955,
            'DPharm': 16141,
            'MPharm': 2354,
            'PharmD': 6393,
            'QC': 29,
            'QP': 231
        }
    };

    // Try to load from cache first
    const cached = localStorage.getItem(CACHE_KEY);
    let cachedStats = null;

    if (cached) {
        try {
            cachedStats = JSON.parse(cached);
            displayAnalytics(cachedStats);
        } catch (e) {
            localStorage.removeItem(CACHE_KEY);
        }
    } else {
        displayAnalytics(fallbackStats);
    }

    try {
        // Single RPC call to get all stats (production grade)
        const { data: stats, error } = await supabaseClient.rpc('get_rx_stats');

        if (error) throw error;

        // If cached total matches live total, data hasn't changed - we're done
        if (cachedStats && cachedStats.total === stats.total) {
            return;
        }


        // Save to cache
        localStorage.setItem(CACHE_KEY, JSON.stringify(stats));

        // Display fresh data
        displayAnalytics(stats);

    } catch (error) {
        console.error('Error loading analytics:', error);
        // Fallback already displayed, no action needed
    }
}

// Display analytics on the page
function displayAnalytics(stats) {

    document.getElementById('totalRecords').textContent = stats.total.toLocaleString();

    if (stats.categories) {

        // Update all categories
        Object.keys(stats.categories).forEach(cat => {
            const elementId = cat.toLowerCase() + 'Count';
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = stats.categories[cat].toLocaleString();
            } else {
            }
        });

    }

    // Set last updated date with time
    const now = new Date();

    const dayName = DAYS[now.getDay()];
    const dayNum = String(now.getDate()).padStart(2, '0');
    const monthName = MONTHS[now.getMonth()];
    const year = now.getFullYear();

    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');

    const dateStr = `${dayNum} ${monthName} ${year}`;
    const timeStr = `${hours}:${minutes}`;

    const lastUpdatedEl = document.getElementById('lastUpdated');
    if (lastUpdatedEl) {
        lastUpdatedEl.textContent = `${dateStr} ${timeStr}`;
    }
}

// Security: Rate limiting (6 requests per 30 seconds)
const rateLimiter = {
    requests: [],
    maxRequests: 6,
    windowMs: 30000, // 30 seconds

    canMakeRequest() {
        const now = Date.now();
        this.requests = this.requests.filter(time => now - time < this.windowMs);
        if (this.requests.length >= this.maxRequests) {
            return false;
        }
        this.requests.push(now);
        return true;
    }
};

// Security: Sanitize search query
function sanitizeQuery(query) {
    // Remove any SQL-like characters and limit length
    return query
        .replace(/[;'"\\]/g, '')  // Remove dangerous chars
        .substring(0, 100);        // Max 100 characters
}

// Perform search
async function performSearch() {
    const rawQuery = document.getElementById('searchInput').value.trim();
    const loadingDiv = document.getElementById('loading');
    const errorDiv = document.getElementById('error');
    const resultsPanel = document.getElementById('resultsPanel');

    // Input validation
    if (rawQuery.length < 3) {
        resultsPanel.style.display = 'none';
        return;
    }

    if (rawQuery.length > 100) {
        errorDiv.innerHTML = '<div class="error">⚠️ Search query too long (max 100 characters)</div>';
        return;
    }

    // Rate limiting
    if (!rateLimiter.canMakeRequest()) {
        errorDiv.innerHTML = '<div class="error">⚠️ Too many requests. Please wait a moment.</div>';
        // Auto-dismiss after 3 seconds
        setTimeout(() => {
            if (errorDiv.innerHTML.includes('Too many requests')) {
                errorDiv.innerHTML = '';
            }
        }, 3000);
        return;
    }

    // Sanitize query
    const query = sanitizeQuery(rawQuery);

    loadingDiv.style.display = 'block';
    resultsPanel.style.display = 'none';
    errorDiv.innerHTML = '';

    try {
        let queryBuilder = supabaseClient
            .from('rx')
            .select('registration_number,name,father_name,category')
            .or(`registration_number.ilike.%${query}%,name.ilike.%${query}%,father_name.ilike.%${query}%`);

        // Apply category filter
        if (currentFilters.category !== 'all') {
            queryBuilder = queryBuilder.eq('category', currentFilters.category);
        }

        const { data, error } = await queryBuilder.limit(100000);

        if (error) throw error;

        currentResults = data;
        currentPage = 1;
        loadingDiv.style.display = 'none';
        resultsPanel.style.display = 'block';

        // Shareable URL removed
        // updateUrlQuery(query);

        sortResults();

    } catch (error) {
        console.error('Search error:', error);
        loadingDiv.style.display = 'none';
        errorDiv.innerHTML = `<div class="error">❌ Search failed. Please try again.</div>`;
    }
}

// Shareable URLs: DISABLED
function checkUrlQuery() {
    // Shareable links functionality removed
    return;
}

// Sort results by registration number (by prefix, then by number ascending)
function sortResults() {
    let sorted = [...currentResults];
    sorted.sort((a, b) => {
        // Extract prefix and number from registration number (e.g., "TS000001" or "TG061028")
        const parseReg = (reg) => {
            const match = reg.match(/^([A-Z]+)(\d+)$/);
            if (match) {
                return { prefix: match[1], num: parseInt(match[2], 10) };
            }
            return { prefix: reg, num: 0 };
        };

        const regA = parseReg(a.registration_number);
        const regB = parseReg(b.registration_number);

        // Sort by prefix first (alphabetically)
        if (regA.prefix !== regB.prefix) {
            return regA.prefix.localeCompare(regB.prefix);
        }
        // Then by number (ascending)
        return regA.num - regB.num;
    });
    currentPage = 1;
    displayResults(sorted);
}

// Load more results
function loadMore() {
    currentPage++;
    displayResults(displayedResults, true);
}

// Display all results (no pagination)
function displayResults(data) {
    const resultsDiv = document.getElementById('results');
    const resultsCount = document.getElementById('resultsCount');

    displayedResults = data;
    resultsCount.textContent = data.length.toLocaleString();

    if (data.length === 0) {
        resultsDiv.innerHTML = '<div class="empty-state">No results found. Try different search terms or filters.</div>';
        return;
    }

    const tableHtml = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Registration Number</th>
                    <th>Name</th>
                    <th>Father's Name</th>
                    <th>Category</th>
                </tr>
            </thead>
            <tbody>
                ${data.map(record => `
                    <tr>
                        <td><span class="reg-number">${escapeHtml(record.registration_number)}</span></td>
                        <td>${escapeHtml(record.name)}</td>
                        <td>${escapeHtml(record.father_name) || 'N/A'}</td>
                        <td><span class="badge ${escapeHtml(record.category).toLowerCase()}">${escapeHtml(record.category)}</span></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    resultsDiv.innerHTML = tableHtml;
}

// Reset search
function resetSearch() {
    // Clear search input
    document.getElementById('searchInput').value = '';

    // Reset filters to "All Categories"
    document.querySelectorAll('.filter-chip').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.value === 'all') {
            btn.classList.add('active');
        }
    });
    currentFilters.category = 'all';

    // Clear results
    currentResults = [];
    displayedResults = [];
    currentPage = 1;

    // Hide results panel
    document.getElementById('resultsPanel').style.display = 'none';
    document.getElementById('error').innerHTML = '';
    document.getElementById('loading').style.display = 'none';

    // Clear URL query parameter
    // updateUrlQuery(''); // Removed: shareable links disabled
}

// Export results to PDF
function exportResults() {
    if (currentResults.length === 0) {
        alert('No results to export. Please perform a search first.');
        return;
    }

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    // Add title
    doc.setFontSize(18);
    doc.setTextColor(0, 204, 102);
    doc.text('TGPC Rx Registry', 14, 20);

    // Add subtitle with date
    doc.setFontSize(10);
    doc.setTextColor(100, 100, 100);
    const dateStr = new Date().toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
    doc.text(`Search Results - ${dateStr}`, 14, 27);
    doc.text(`Total Records: ${currentResults.length}`, 14, 32);

    // Prepare table data
    const tableData = currentResults.map(record => [
        record.registration_number,
        record.name,
        record.father_name || 'N/A',
        record.category
    ]);

    // Add table
    doc.autoTable({
        startY: 38,
        head: [['Registration Number', 'Name', 'Father\'s Name', 'Category']],
        body: tableData,
        theme: 'striped',
        headStyles: {
            fillColor: [0, 204, 102],
            textColor: [255, 255, 255],
            fontStyle: 'bold',
            fontSize: 10
        },
        bodyStyles: {
            fontSize: 9
        },
        alternateRowStyles: {
            fillColor: [250, 250, 250]
        },
        columnStyles: {
            0: { cellWidth: 40 },
            1: { cellWidth: 60 },
            2: { cellWidth: 50 },
            3: { cellWidth: 30 }
        },
        margin: { top: 38, left: 14, right: 14 }
    });

    // Save PDF
    doc.save(`tgpc_rx_search_${new Date().toISOString().split('T')[0]}.pdf`);
}

// Export results to CSV
function exportCSV() {
    if (currentResults.length === 0) {
        alert('No results to export. Please perform a search first.');
        return;
    }

    // CSV header
    const headers = ['Registration Number', 'Name', 'Father Name', 'Category'];

    // Build CSV content
    const csvRows = [headers.join(',')];

    currentResults.forEach(record => {
        const row = [
            `"${record.registration_number || ''}"`,
            `"${(record.name || '').replace(/"/g, '""')}"`,
            `"${(record.father_name || '').replace(/"/g, '""')}"`,
            `"${record.category || ''}"`
        ];
        csvRows.push(row.join(','));
    });

    const csvContent = csvRows.join('\n');

    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'tgpc_rx_search_' + new Date().toISOString().split('T')[0] + '.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
}
