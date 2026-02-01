// API base URL - detect if frontend and backend are on same origin
// If frontend is on port 4000 (dev server) or different port, use backend URL explicitly
// Otherwise use relative URL (production or when served from backend on port 8000)
const getApiBaseUrl = () => {
    const port = window.location.port;
    const hostname = window.location.hostname;
    
    // If on port 8000 or no port (default), assume backend is on same origin
    if (port === '8000' || port === '') {
        return window.location.origin;
    }
    
    // Development mode: frontend on different port, backend on 8000
    // Use explicit backend URL
    return `http://${hostname}:8000`;
};

const API_BASE_URL = getApiBaseUrl();
console.log('API Base URL:', API_BASE_URL);

// Initialize map with zoom control at bottom-left
// Centered on Central Europe (around Alps region)
const map = L.map('map', {
    zoomControl: false
}).setView([47.5, 10.5], 6);

// Add zoom control at bottom-left
L.control.zoom({
    position: 'bottomleft'
}).addTo(map);

// Define available map tile layers
const mapLayers = {
    'Standard': L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }),
    'Cycling': L.tileLayer('https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; CyclOSM &copy; OpenStreetMap contributors'
    }),
    'Topo': L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        maxZoom: 17,
        attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a>',
        subdomains: ['a', 'b', 'c']
    }),
    'Satellite': L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: 'Tiles &copy; Esri'
    })
};

// Set default layer
let currentMapLayer = 'Standard';
mapLayers[currentMapLayer].addTo(map);

// Add Leaflet layer control at bottom-left
const baseMaps = {
    "Standard": mapLayers['Standard'],
    "Cycling": mapLayers['Cycling'],
    "Topo": mapLayers['Topo'],
    "Satellite": mapLayers['Satellite']
};

L.control.layers(baseMaps, null, {
    position: 'bottomleft',
    collapsed: true
}).addTo(map);

// Function to check if a map type is a satellite view
function isSatelliteMap(layerName) {
    return layerName === 'Satellite';
}

// Route color options - click track to cycle through
const routeColors = [
    { color: '#666', name: 'Gray' },
    { color: '#e63946', name: 'Red' },
    { color: '#2a9d8f', name: 'Teal' },
    { color: '#e76f51', name: 'Orange' },
    { color: '#9b59b6', name: 'Purple' },
    { color: '#3498db', name: 'Blue' },
    { color: '#FFD700', name: 'Yellow' }
];
let currentRouteColorIndex = 0;

// Function to get route line weight based on screen size
function getRouteWeight() {
    const isMobile = window.innerWidth < 900;
    return isMobile ? 4 : 3;
}

// Function to cycle route color on click
function cycleRouteColor() {
    currentRouteColorIndex = (currentRouteColorIndex + 1) % routeColors.length;
    updateRouteLineStyle();
    const colorName = routeColors[currentRouteColorIndex].name;
    updateStatus(`Track color: ${colorName}`);
    setTimeout(() => updateStatus(''), 1500);
}

// Function to update route line style based on map type and selected color
function updateRouteLineStyle() {
    if (!currentRoute) return;

    const weight = getRouteWeight();
    const selectedColor = routeColors[currentRouteColorIndex].color;

    currentRoute.setStyle({
        color: selectedColor,
        weight: weight,
        opacity: 1.0
    });
}

// Listen for layer changes to update route style
map.on('baselayerchange', function(e) {
    currentMapLayer = e.name;
    updateRouteLineStyle();
});

// Add scale control to bottom right
L.control.scale({ position: 'bottomright' }).addTo(map);

// User location tracking
let userLocationMarker = null;
let userLocationCircle = null;
let watchPositionId = null;
let locationControlBtn = null;

// Create custom icon for user location (blue pulsing dot)
const userLocationIcon = L.divIcon({
    className: 'user-location-icon',
    html: '<div class="user-location-dot"></div><div class="user-location-pulse"></div>',
    iconSize: [20, 20],
    iconAnchor: [10, 10]
});

// Function to show user's location on map
function showUserLocation() {
    if (!navigator.geolocation) {
        updateStatus('Geolocation not supported');
        setTimeout(() => updateStatus(''), 3000);
        return;
    }

    // Toggle location tracking
    if (watchPositionId !== null) {
        // Stop tracking
        navigator.geolocation.clearWatch(watchPositionId);
        watchPositionId = null;
        if (userLocationMarker) {
            map.removeLayer(userLocationMarker);
            userLocationMarker = null;
        }
        if (userLocationCircle) {
            map.removeLayer(userLocationCircle);
            userLocationCircle = null;
        }
        if (locationControlBtn) {
            locationControlBtn.classList.remove('active');
        }
        return;
    }

    // Start tracking
    if (locationControlBtn) {
        locationControlBtn.classList.add('active');
    }
    updateStatus('Getting location...');

    const onLocationFound = (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        const accuracy = position.coords.accuracy;

        // Remove old markers
        if (userLocationMarker) {
            map.removeLayer(userLocationMarker);
        }
        if (userLocationCircle) {
            map.removeLayer(userLocationCircle);
        }

        // Add accuracy circle
        userLocationCircle = L.circle([lat, lng], {
            radius: accuracy,
            color: '#3b82f6',
            fillColor: '#3b82f6',
            fillOpacity: 0.1,
            weight: 1
        }).addTo(map);

        // Add location marker
        userLocationMarker = L.marker([lat, lng], {
            icon: userLocationIcon,
            zIndexOffset: 1000
        }).addTo(map);

        updateStatus('');
    };

    const onLocationError = (error) => {
        if (locationControlBtn) {
            locationControlBtn.classList.remove('active');
        }
        watchPositionId = null;
        let message = 'Location error';
        switch (error.code) {
            case error.PERMISSION_DENIED:
                message = 'Location permission denied';
                break;
            case error.POSITION_UNAVAILABLE:
                message = 'Location unavailable';
                break;
            case error.TIMEOUT:
                message = 'Location request timed out';
                break;
        }
        updateStatus(message);
        setTimeout(() => updateStatus(''), 3000);
    };

    // Get initial position and pan to it
    navigator.geolocation.getCurrentPosition(
        (position) => {
            onLocationFound(position);
            map.setView([position.coords.latitude, position.coords.longitude], Math.max(map.getZoom(), 13));
        },
        onLocationError,
        { enableHighAccuracy: true, timeout: 10000 }
    );

    // Watch position for updates
    watchPositionId = navigator.geolocation.watchPosition(
        onLocationFound,
        onLocationError,
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 }
    );
}

// Location control (Leaflet control at bottom-left)
const LocationControl = L.Control.extend({
    onAdd: function(map) {
        const container = L.DomUtil.create('div', 'leaflet-control-location leaflet-bar');
        const btn = L.DomUtil.create('a', 'leaflet-control-location-btn', container);
        btn.href = '#';
        btn.title = 'My Location';
        btn.innerHTML = '<i class="fas fa-location-crosshairs"></i>';
        btn.setAttribute('role', 'button');
        btn.setAttribute('aria-label', 'My Location');

        locationControlBtn = btn;

        L.DomEvent.disableClickPropagation(container);
        L.DomEvent.on(btn, 'click', function(e) {
            L.DomEvent.preventDefault(e);
            showUserLocation();
        });

        return container;
    }
});

new LocationControl({ position: 'bottomleft' }).addTo(map);


let currentRoute = null;
let currentRouteID = null;
let currentMarkers = [];
// Map to link POI data to markers and table rows: { poiId: { marker: L.Marker, row: HTMLElement, starred: boolean, data: POI } }
let poiMarkerMap = new Map();
// Set to store starred POI IDs for future GPX export
let starredPOIs = new Set();

// Timeline data
let elevationData = [];
let totalRouteDistance = 0;
let timelineSettings = {
    speed: 25        // km/h
};
let timelineHoverMarker = null; // Blue dot marker for timeline hover

// POI icon mapping - loaded from config file
let POI_ICON_MAP = {};

// Load POI icon configuration from JSON file
async function loadPOIIcons() {
    try {
        const response = await fetch('static/poi-icons.json');
        POI_ICON_MAP = await response.json();
    } catch (error) {
        console.error('Failed to load POI icon config, using defaults:', error);
        // Fallback to default icons if config file can't be loaded
        POI_ICON_MAP = {
            "public_toilets": { icon: "fa-circle", color: "#4a90e2" },
            "bakeries": { icon: "fa-circle", color: "#d4a574" },
            "gas_stations": { icon: "fa-circle", color: "#e74c3c" },
            "grocery_stores": { icon: "fa-circle", color: "#27ae60" },
            "water_fountains": { icon: "fa-circle", color: "#3498db" },
            "bicycle_shops": { icon: "fa-circle", color: "#2c3e50" },
            "bicycle_vending": { icon: "fa-circle", color: "#9b59b6" },
            "vending_machines": { icon: "fa-circle", color: "#f39c12" },
            "camping_hotels": { icon: "fa-circle", color: "#16a085" }
        };
    }
}

// Helper function to create a custom POI icon
function createPOIIcon(poiType) {
    const iconConfig = POI_ICON_MAP[poiType] || { icon: "fa-circle", color: "#7fb800" };
    const iconHtml = `<i class="fas ${iconConfig.icon}" style="color: ${iconConfig.color}; font-size: 16px;"></i>`;
    
    return L.divIcon({
        html: iconHtml,
        className: 'custom-poi-icon',
        iconSize: [20, 20],
        iconAnchor: [10, 10],
        popupAnchor: [0, -10]
    });
}

// Helper function to format POI type label for display
function formatPOITypeLabel(poiType) {
    if (poiType === 'camping_hotels') {
        return 'Accommodation';
    }
    return poiType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function updateStatus(message) {
    const statusElement = document.getElementById('status-message');
    if (!statusElement) return;
    statusElement.textContent = message;
    updateToolbarCenterVisibility();
}

// Update toolbar center visibility based on content
function updateToolbarCenterVisibility() {
    const toolbarCenter = document.getElementById('toolbar-center');
    const filenameDisplay = document.getElementById('filename-display');
    const statusMessage = document.getElementById('status-message');

    if (!toolbarCenter) return;

    const hasFilename = filenameDisplay && filenameDisplay.style.display !== 'none' && filenameDisplay.textContent;
    const hasStatus = statusMessage && statusMessage.textContent;

    if (hasFilename || hasStatus) {
        toolbarCenter.style.display = 'flex';
    } else {
        toolbarCenter.style.display = 'none';
    }
}

// Update POI count badge
function updatePOICount() {
    const countBadge = document.getElementById('poi-count');
    const poiTable = document.getElementById('poi-table');
    const poiEmpty = document.getElementById('poi-empty');

    if (!countBadge) return;

    const count = poiMarkerMap.size;
    countBadge.textContent = count;

    // Show/hide empty state vs table
    if (poiTable && poiEmpty) {
        if (count > 0) {
            poiTable.style.display = 'table';
            poiEmpty.style.display = 'none';
        } else {
            poiTable.style.display = 'none';
            poiEmpty.style.display = 'flex';
        }
    }
}

// Settings management
const ALL_POI_TYPES = ['public_toilets', 'bakeries', 'gas_stations', 'grocery_stores', 'water_fountains', 'bicycle_shops', 'bicycle_vending', 'vending_machines', 'camping_hotels', 'sport_areas'];

function getDefaultPoiSettings() {
    return {
        public_toilets: {
            maxDeviation: 100, // meters
            deduplicationRadius: 3000 // meters
        },
        bakeries: {
            maxDeviation: 250, // meters
            deduplicationRadius: 5000 // meters
        },
        gas_stations: {
            maxDeviation: 100, // meters
            deduplicationRadius: 5000 // meters
        },
        grocery_stores: {
            maxDeviation: 250, // meters
            deduplicationRadius: 5000 // meters
        },
        water_fountains: {
            maxDeviation: 100, // meters
            deduplicationRadius: 2000 // meters
        },
        bicycle_shops: {
            maxDeviation: 1000, // meters
            deduplicationRadius: 4000 // meters
        },
        bicycle_vending: {
            maxDeviation: 1000, // meters
            deduplicationRadius: 4000 // meters
        },
        vending_machines: {
            maxDeviation: 100, // meters
            deduplicationRadius: 1000 // meters
        },
        camping_hotels: {
            maxDeviation: 500, // meters
            deduplicationRadius: 5000 // meters
        },
        sport_areas: {
            maxDeviation: 500, // meters
            deduplicationRadius: 3000 // meters
        }
    };
}

const DEFAULT_SETTINGS = {
    poiTypes: ALL_POI_TYPES.filter(type => type !== 'camping_hotels' && type !== 'sport_areas'),
    poiSettings: getDefaultPoiSettings()
};

function loadSettings() {
    try {
        const saved = localStorage.getItem('poiSettings');
        if (saved) {
            const settings = JSON.parse(saved);
            // Migrate old settings format if needed
            if (settings.maxDeviation !== undefined) {
                // Old format - convert to new format
                const poiSettings = getDefaultPoiSettings();
                ALL_POI_TYPES.forEach(poiType => {
                    poiSettings[poiType] = {
                        maxDeviation: settings.maxDeviation || 1000,
                        deduplicationRadius: settings.deduplicationRadius || 1000
                    };
                });
                return {
                    poiTypes: settings.poiTypes || DEFAULT_SETTINGS.poiTypes,
                    poiSettings: poiSettings
                };
            }
            return {
                poiTypes: settings.poiTypes || DEFAULT_SETTINGS.poiTypes,
                poiSettings: settings.poiSettings || getDefaultPoiSettings()
            };
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
    return { ...DEFAULT_SETTINGS };
}

function saveSettings(settings) {
    try {
        localStorage.setItem('poiSettings', JSON.stringify(settings));
    } catch (error) {
        console.error('Error saving settings:', error);
    }
}

function applySettings(settings) {
    // Apply POI type checkboxes
    document.querySelectorAll('.poi-checkbox').forEach(checkbox => {
        checkbox.checked = settings.poiTypes.includes(checkbox.value);
    });
    
    // Apply per-POI-type input fields
    ALL_POI_TYPES.forEach(poiType => {
        const poiSetting = settings.poiSettings[poiType] || { maxDeviation: 1000, deduplicationRadius: 1000 };
        const maxDevInput = document.querySelector(`.poi-max-deviation[data-poi-type="${poiType}"]`);
        const dedupInput = document.querySelector(`.poi-deduplication-radius[data-poi-type="${poiType}"]`);
        if (maxDevInput) maxDevInput.value = poiSetting.maxDeviation;
        if (dedupInput) dedupInput.value = poiSetting.deduplicationRadius;
    });
}

document.getElementById('gpx-upload').addEventListener('change', async function(event) {
    const file = this.files[0];
    if (!file) {
        updateStatus('Error: No file selected');
        setTimeout(() => updateStatus(''), 3000);
        return;
    }
    
    const filenameDisplay = document.getElementById('filename-display');
    filenameDisplay.textContent = file.name;
    filenameDisplay.style.display = 'inline-block';
    updateToolbarCenterVisibility();
    updateStatus('Uploading GPX...');

    const formData = new FormData();
    formData.append('file', file);

    console.log('Uploading file:', file.name, 'Size:', file.size, 'Type:', file.type);
    console.log('API URL:', `${API_BASE_URL}/gpx/upload`);

    try {
        const response = await fetch(`${API_BASE_URL}/gpx/upload`, {
            method: 'POST',
            body: formData
            // Don't set Content-Type - browser will set it automatically with boundary
        });

        if (!response.ok) {
            // Handle error response from backend
            let errorMessage = 'Failed to upload GPX file';
            try {
                const errorData = await response.json();
                errorMessage = errorData.detail || errorMessage;
            } catch (parseError) {
                // If JSON parsing fails, use status text
                errorMessage = response.statusText || errorMessage;
            }
            console.error('Error uploading GPX file:', errorMessage);
            updateStatus(`Error: ${errorMessage}`);
            setTimeout(() => updateStatus(''), 5000);
            return;
        }

        const data = await response.json();
        currentRouteID = data.route_id;

        // Store elevation data for timeline
        elevationData = data.elevation_profile || [];
        totalRouteDistance = data.total_distance || 0;

        updateStatus('Parsing route...');

        if (currentRoute){
            map.removeLayer(currentRoute);
        }

        const routePoints = data.coordinates.map(coord => [coord.lat, coord.lon]);

        currentRoute = L.polyline(routePoints, {color: '#666', weight: getRouteWeight()}).addTo(map);

        // Add click handler to cycle route color
        currentRoute.on('click', cycleRouteColor);

        // Update route line style based on current map type
        updateRouteLineStyle();

        // Fit bounds with padding to account for UI elements
        // On mobile (< 900px), POI panel is at bottom; on desktop, it's on the right
        const isMobile = window.innerWidth < 900;
        const padding = isMobile
            ? { paddingTopLeft: [20, 100], paddingBottomRight: [20, 60] }  // Mobile: top padding for controls, bottom for POI panel toggle
            : { paddingTopLeft: [20, 80], paddingBottomRight: [520, 20] }; // Desktop: right padding for POI panel
        map.fitBounds(currentRoute.getBounds(), padding);

        // Clear POI list when uploading a new GPX
        clearPOIList();

        // Update download button state
        updateDownloadButtonState();

        await loadPOIs();

    } catch (error) {
        // Handle network errors or other exceptions
        console.error('Error uploading GPX file:', error);
        console.error('Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
        let errorMessage = 'Failed to upload GPX file';
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            errorMessage = 'Network error: Could not connect to server. Please ensure the backend is running on port 8000.';
        } else {
            errorMessage = error.message || 'Failed to upload GPX file. Please check your connection and try again.';
        }
        updateStatus(`Error: ${errorMessage}`);
        setTimeout(() => updateStatus(''), 5000);
    }
    });

// Helper function to generate a stable POI ID based on coordinates and type
function generatePOIId(lat, lon, poiType, index = 0) {
    // Use coordinates and type for stable ID (round to 6 decimal places for matching)
    const latRounded = parseFloat(lat).toFixed(6);
    const lonRounded = parseFloat(lon).toFixed(6);
    return `${latRounded}_${lonRounded}_${poiType}_${index}`;
}

// Helper function to add a POI to the map and table
function addPOIToMapAndTable(markerData, poi, poiTableBody, startIndex = 0) {
    // Generate stable POI ID based on coordinates and type
    const poiId = generatePOIId(markerData.lat, markerData.lon, markerData.poi_type, startIndex);
    
    // Create enriched popup content
    let popupContent = `<strong>${markerData.name}</strong><br>`;
    if (markerData.poi_type) {
        const typeLabel = formatPOITypeLabel(markerData.poi_type);
        popupContent += `<b>Type:</b> ${typeLabel}<br>`;
    }
    // Check price_range in both markerData and poi (fallback)
    const priceRange = markerData.price_range || poi?.price_range;
    if (priceRange && priceRange.trim() !== '') {
        popupContent += `<b>Price:</b> ${priceRange}<br>`;
    }
    if (markerData.opening_hours) {
        popupContent += `<b>Hours:</b> ${markerData.opening_hours}<br>`;
    }
    if (markerData.url) {
        popupContent += `<a href="${markerData.url}" target="_blank" rel="noopener noreferrer">🌐 Website</a><br>`;
    }
    if (markerData.google_maps_link) {
        popupContent += `<a href="${markerData.google_maps_link}" target="_blank" rel="noopener noreferrer">📍 Open in Google Maps</a>`;
    }
    
    // Create marker
    const icon = createPOIIcon(markerData.poi_type || 'gas_stations');
    const marker = L.marker([markerData.lat, markerData.lon], { icon: icon })
        .bindPopup(popupContent)
        .addTo(map);
    currentMarkers.push(marker);
    
    // Store marker reference
    marker.poiId = poiId;
    marker.starred = false;
    
    // Create table row
    const row = document.createElement('tr');
    row.dataset.poiId = poiId;
    
    // Format combined POI cell with icon+type on first line, name on second
    let poiCell = '';
    if (poi.poi_type) {
        const iconConfig = POI_ICON_MAP[poi.poi_type] || { icon: "fa-circle", color: "#7fb800" };
        const typeLabel = formatPOITypeLabel(poi.poi_type);
        poiCell = `<div class="poi-cell-type"><i class="fas ${iconConfig.icon}" style="color: ${iconConfig.color};"></i> ${typeLabel}</div>`;
        if (poi.name && poi.name.trim() !== '' && poi.name !== typeLabel) {
            poiCell += `<div class="poi-cell-name">${poi.name}</div>`;
        }
    } else {
        poiCell = `<div class="poi-cell-type"><span style="color: var(--text-muted);">Unknown</span></div>`;
        if (poi.name && poi.name.trim() !== '') {
            poiCell += `<div class="poi-cell-name">${poi.name}</div>`;
        }
    }
    
    // Create combined actions cell with links and action buttons (right-aligned)
    let actionsCell = '<div class="poi-actions">';
    // Links first (optional)
    if (poi.url) {
        actionsCell += `<a href="${poi.url}" target="_blank" rel="noopener noreferrer" class="poi-link-btn" title="Website">
            <i class="fas fa-link"></i>
        </a>`;
    }
    if (poi.google_maps_link) {
        actionsCell += `<a href="${poi.google_maps_link}" target="_blank" rel="noopener noreferrer" class="poi-link-btn" title="Google Maps">
            <i class="fas fa-map-marker-alt"></i>
        </a>`;
    }
    // Action buttons (always visible)
    actionsCell += `
        <button class="poi-action-btn poi-star-btn" data-poi-id="${poiId}" title="Star POI">
            <i class="far fa-star"></i>
        </button>
        <button class="poi-action-btn poi-delete-btn" data-poi-id="${poiId}" title="Delete POI">
            <i class="fas fa-trash"></i>
        </button>
    </div>`;

    row.innerHTML = `
        <td>${poi.distance}</td>
        <td>${poi.deviation}</td>
        <td>${poiCell}</td>
        <td>${poi.opening_hours || 'n/a'}</td>
        <td>${actionsCell}</td>
    `;
    
    // Add click handler for row (opens popup on map)
    row.addEventListener('click', (e) => {
        // Don't trigger if clicking on action buttons or link buttons
        if (e.target.closest('.poi-actions')) return;
        
        marker.openPopup();
        map.panTo([markerData.lat, markerData.lon]);
    });
    
    // Add click handler for star button
    const starBtn = row.querySelector('.poi-star-btn');
    starBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleStarPOI(poiId);
    });
    
    // Add click handler for delete button
    const deleteBtn = row.querySelector('.poi-delete-btn');
    deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        deletePOI(poiId);
    });

    // Add hover handlers to show/hide indicator on timeline
    row.addEventListener('mouseenter', () => {
        if (markerData.distance_on_route !== undefined) {
            showPOIHoverIndicator(markerData.distance_on_route);
        }
    });
    row.addEventListener('mouseleave', () => {
        hidePOIHoverIndicator();
    });

    poiTableBody.appendChild(row);
    
    // Store mapping - include numeric distance values from markers if available
    const poiData = { ...markerData, ...poi };
    // Preserve numeric distance values from markers if they exist
    if (markerData.distance_on_route !== undefined) {
        poiData.distance_on_route = markerData.distance_on_route;
    }
    if (markerData.distance_to_route !== undefined) {
        poiData.distance_to_route = markerData.distance_to_route;
    }
    
    poiMarkerMap.set(poiId, {
        marker: marker,
        row: row,
        starred: false,
        data: poiData
    });
}

// Helper function to clear all POIs from map and table
function clearPOIList() {
    // Clear existing markers
    currentMarkers.forEach(marker => {
        map.removeLayer(marker);
    });
    currentMarkers = [];
    // Clear POI mapping
    poiMarkerMap.clear();
    starredPOIs.clear();

    // Clear POI table body immediately
    const poiTableBody = document.getElementById('poi-tbody');
    if (poiTableBody) {
        poiTableBody.innerHTML = '';
    }

    // Update POI count badge
    updatePOICount();
}

async function loadPOIs() {
        // Clear existing POIs
        clearPOIList();
        
    // Load settings from localStorage
    const settings = loadSettings();
    
    // Collect selected POI types from settings
    const selectedPOITypes = settings.poiTypes;
    
    // Build per-POI-type settings dictionary (convert meters to kilometers)
    const poiSettings = {};
    selectedPOITypes.forEach(poiType => {
        const poiSetting = settings.poiSettings[poiType] || { maxDeviation: 1000, deduplicationRadius: 1000 };
        poiSettings[poiType] = {
            max_deviation_km: poiSetting.maxDeviation / 1000,
            deduplication_radius_km: poiSetting.deduplicationRadius / 1000
        };
    });
    
    // Calculate max distance for bounding box (use the maximum of all selected POI types)
    const maxDistanceKm = Math.max(...selectedPOITypes.map(type => {
        const setting = settings.poiSettings[type] || { maxDeviation: 1000 };
        return setting.maxDeviation / 1000;
    }));
    
    // Build query string with selected POI types and parameters
    const params = new URLSearchParams();
    selectedPOITypes.forEach(type => {
        params.append('poi_types', type);
    });
    params.append('max_distance_km', maxDistanceKm.toString());
    // Send per-POI-type settings as JSON
    if (Object.keys(poiSettings).length > 0) {
        params.append('poi_settings_json', JSON.stringify(poiSettings));
    }
    
    return new Promise((resolve, reject) => {
        const url = `${API_BASE_URL}/pois/${currentRouteID}?${params.toString()}`;
        const eventSource = new EventSource(url);
        
        // Get POI table body reference (will be reused)
        const poiTableBody = document.getElementById('poi-tbody');
        
        eventSource.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                
                if (data.type === 'progress') {
                    // Update status with current POI type being queried
                    updateStatus(`Querying ${data.poi_type_display} (${data.current}/${data.total})...`);
                } else if (data.type === 'poi_batch') {
                    // Handle incremental POI batch - display POIs as they arrive
                    updateStatus(`Found ${data.markers.length} ${data.poi_type_display}...`);
                    
                    // Add each POI from the batch to the map and table
                    data.markers.forEach((markerData, index) => {
                        const poi = data.table[index];
                        if (!poi) return;
                        addPOIToMapAndTable(markerData, poi, poiTableBody, index);
                    });

                    // Update download button state and POI count after each batch
                    updateDownloadButtonState();
                    updatePOICount();
                } else if (data.type === 'complete') {
                    eventSource.close();
                    
                    updateStatus('Finalizing POIs...');
        
                    // Debug: log the data to see what we're receiving
                    console.log('Final POI Data received:', data);
                    if (data.table && data.table.length > 0) {
                        console.log('First POI example:', data.table[0]);
                    }
                    
                    // For the final complete message, we need to handle deduplication
                    // Since POIs were already added incrementally, we'll replace with the final deduplicated list
                    
                    // Preserve starred POIs before clearing - store by coordinates and type for matching
                    // Use a more flexible matching approach: match by lat, lon, and type (without index)
                    const starredPOIsData = new Map();
                    starredPOIs.forEach(starredId => {
                        const poiData = poiMarkerMap.get(starredId);
                        if (poiData && poiData.data) {
                            // Create a key based on coordinates and type for matching (without index)
                            const latRounded = parseFloat(poiData.data.lat).toFixed(6);
                            const lonRounded = parseFloat(poiData.data.lon).toFixed(6);
                            const key = `${latRounded}_${lonRounded}_${poiData.data.poi_type}`;
                            starredPOIsData.set(key, true);
                        }
                    });
                    
                    // Clear existing markers and table rows
                    currentMarkers.forEach(marker => {
                        map.removeLayer(marker);
                    });
                    currentMarkers = [];
                    poiMarkerMap.clear();
                    starredPOIs.clear();
                    poiTableBody.innerHTML = '';
                    
                    // Add all POIs from the final deduplicated list
                    data.markers.forEach((markerData, index) => {
                        const poi = data.table[index];
                        if (!poi) return;
                        addPOIToMapAndTable(markerData, poi, poiTableBody, index);
                        
                        // Restore starred state if this POI was previously starred
                        // Match by coordinates and type (without index)
                        const latRounded = parseFloat(markerData.lat).toFixed(6);
                        const lonRounded = parseFloat(markerData.lon).toFixed(6);
                        const key = `${latRounded}_${lonRounded}_${markerData.poi_type}`;
                        if (starredPOIsData.has(key)) {
                            // This POI was starred before, restore the starred state
                            const poiId = generatePOIId(markerData.lat, markerData.lon, markerData.poi_type, index);
                            const poiData = poiMarkerMap.get(poiId);
                            if (poiData) {
                                toggleStarPOI(poiId);
                            }
                        }
                    });

                    updateStatus('Complete!');
                    setTimeout(() => updateStatus(''), 2000);
                    // Update download button state and POI count after POIs are loaded
                    updateDownloadButtonState();
                    updatePOICount();
                    resolve();
                } else if (data.type === 'error') {
                    eventSource.close();
                    updateStatus(`Error: ${data.error}`);
                    setTimeout(() => updateStatus(''), 3000);
                    alert(data.error || 'Failed to load POIs. Please try again.');
                    reject(new Error(data.error));
                }
    } catch (error) {
                console.error('Error parsing SSE data:', error);
                eventSource.close();
                updateStatus('Error: Failed to parse response');
                setTimeout(() => updateStatus(''), 3000);
                reject(error);
            }
        };
        
        eventSource.onerror = function(error) {
            console.error('EventSource error:', error);
            eventSource.close();
            updateStatus('Error: Connection lost');
            setTimeout(() => updateStatus(''), 3000);
            reject(new Error('Connection lost'));
        };
    });
}

// Helper function to toggle POI list visibility - removed, list is always visible now

// Helper function to toggle star state of a POI
function toggleStarPOI(poiId) {
    const poiData = poiMarkerMap.get(poiId);
    if (!poiData) return;

    const isStarred = poiData.starred;
    poiData.starred = !isStarred;
    poiData.marker.starred = !isStarred;

    const starBtn = poiData.row.querySelector('.poi-star-btn');
    const starIcon = starBtn.querySelector('i');

    if (poiData.starred) {
        starBtn.classList.add('starred');
        starIcon.className = 'fas fa-star';
        starredPOIs.add(poiId);
        poiData.row.classList.add('starred');
    } else {
        starBtn.classList.remove('starred');
        starIcon.className = 'far fa-star';
        starredPOIs.delete(poiId);
        poiData.row.classList.remove('starred');
    }

    // Update download button state
    updateDownloadButtonState();

    // Refresh timeline if visible
    refreshTimelineIfVisible();
}

// Helper function to update download button state
function updateDownloadButtonState() {
    const downloadBtn = document.getElementById('download-gpx-btn');
    if (!downloadBtn) return;
    
    const hasRoute = currentRouteID !== null;
    const hasStarredPOIs = starredPOIs.size > 0;
    
    downloadBtn.disabled = !hasRoute || !hasStarredPOIs;
}

// Function to download GPX with starred POIs
async function downloadGPXWithStarredPOIs() {
    if (!currentRouteID) {
        updateStatus('Error: No route loaded');
        setTimeout(() => updateStatus(''), 3000);
        return;
    }
    
    if (starredPOIs.size === 0) {
        updateStatus('Error: No starred POIs to download');
        setTimeout(() => updateStatus(''), 3000);
        return;
    }
    
    try {
        updateStatus('Preparing download...');
        
        // Collect starred POI data
        const starredPOIsData = [];
        starredPOIs.forEach(poiId => {
            const poiData = poiMarkerMap.get(poiId);
            if (poiData && poiData.data) {
                // Include numeric distance values if available, otherwise use formatted strings
                const poiInfo = {
                    lat: poiData.data.lat,
                    lon: poiData.data.lon,
                    name: poiData.data.name,
                    poi_type: poiData.data.poi_type || 'unknown',
                    opening_hours: poiData.data.opening_hours || null,
                    url: poiData.data.url || null,
                    google_maps_link: poiData.data.google_maps_link || '',
                    price_range: poiData.data.price_range || null
                };
                
                // Add numeric distance values if available
                if (poiData.data.distance_on_route !== undefined) {
                    poiInfo.distance_on_route = poiData.data.distance_on_route;
                }
                if (poiData.data.distance_to_route !== undefined) {
                    poiInfo.distance_to_route = poiData.data.distance_to_route;
                }
                
                // Also include formatted strings as fallback
                const row = poiData.row;
                if (row && row.cells.length >= 2) {
                    poiInfo.distance = row.cells[0].textContent.trim();
                    poiInfo.deviation = row.cells[1].textContent.trim();
                }
                
                starredPOIsData.push(poiInfo);
            }
        });
        
        // Call backend endpoint with POST to avoid URL length limits
        const url = `${API_BASE_URL}/gpx/download/${currentRouteID}`;
        
        // Fetch and trigger download using POST with JSON body
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(starredPOIsData)
        });
        
        if (!response.ok) {
            let errorMessage = 'Failed to download GPX file';
            try {
                const errorData = await response.json();
                errorMessage = errorData.detail || errorMessage;
            } catch (parseError) {
                // If JSON parsing fails, use status text
                errorMessage = response.statusText || errorMessage;
            }
            
            // Provide more helpful error messages
            if (response.status === 404) {
                if (errorMessage.includes('Route not found')) {
                    errorMessage = 'Route not found. Please upload your GPX file again.';
                }
            }
            
            throw new Error(errorMessage);
        }
        
        // Get filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'route_with_pois.gpx';
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="(.+)"/);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        }
        
        // Create blob and trigger download
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);
        
        updateStatus('Download complete!');
        setTimeout(() => updateStatus(''), 2000);

    } catch (error) {
        console.error('Error downloading GPX file:', error);
        updateStatus(`Error: ${error.message}`);
        setTimeout(() => updateStatus(''), 3000);
    }
}

// Function to show download format dialog
function showDownloadFormatDialog() {
    if (!currentRouteID) {
        updateStatus('Error: No route loaded');
        setTimeout(() => updateStatus(''), 3000);
        return;
    }

    if (starredPOIs.size === 0) {
        updateStatus('Error: No starred POIs to download');
        setTimeout(() => updateStatus(''), 3000);
        return;
    }

    const modal = document.getElementById('download-format-modal');
    if (modal) {
        modal.classList.add('active');
    }
}

// Function to hide download format dialog
function hideDownloadFormatDialog() {
    const modal = document.getElementById('download-format-modal');
    if (modal) {
        modal.classList.remove('active');
    }
}

// Function to get starred POI data for download
function getStarredPOIsData() {
    const starredPOIsData = [];
    starredPOIs.forEach(poiId => {
        const poiData = poiMarkerMap.get(poiId);
        if (poiData && poiData.data) {
            const poiInfo = {
                lat: poiData.data.lat,
                lon: poiData.data.lon,
                name: poiData.data.name,
                poi_type: poiData.data.poi_type || 'unknown',
                opening_hours: poiData.data.opening_hours || null,
                url: poiData.data.url || null,
                google_maps_link: poiData.data.google_maps_link || '',
                price_range: poiData.data.price_range || null
            };

            if (poiData.data.distance_on_route !== undefined) {
                poiInfo.distance_on_route = poiData.data.distance_on_route;
            }
            if (poiData.data.distance_to_route !== undefined) {
                poiInfo.distance_to_route = poiData.data.distance_to_route;
            }

            const row = poiData.row;
            if (row && row.cells.length >= 2) {
                poiInfo.distance = row.cells[0].textContent.trim();
                poiInfo.deviation = row.cells[1].textContent.trim();
            }

            starredPOIsData.push(poiInfo);
        }
    });
    return starredPOIsData;
}

// Function to download KML with starred POIs
async function downloadKMLWithStarredPOIs() {
    hideDownloadFormatDialog();

    try {
        updateStatus('Preparing KML download...');

        const starredPOIsData = getStarredPOIsData();

        const url = `${API_BASE_URL}/kml/download/${currentRouteID}`;

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(starredPOIsData)
        });

        if (!response.ok) {
            let errorMessage = 'Failed to download KML file';
            try {
                const errorData = await response.json();
                errorMessage = errorData.detail || errorMessage;
            } catch (parseError) {
                errorMessage = response.statusText || errorMessage;
            }
            throw new Error(errorMessage);
        }

        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'route_with_pois.kml';
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="(.+)"/);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        }

        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);

        updateStatus('KML download complete!');
        setTimeout(() => updateStatus(''), 2000);

    } catch (error) {
        console.error('Error downloading KML file:', error);
        updateStatus(`Error: ${error.message}`);
        setTimeout(() => updateStatus(''), 3000);
    }
}

// Wrapper for GPX download from dialog
async function downloadGPXFromDialog() {
    hideDownloadFormatDialog();
    await downloadGPXWithStarredPOIs();
}

// Helper function to delete a POI
function deletePOI(poiId) {
    const poiData = poiMarkerMap.get(poiId);
    if (!poiData) return;

    // Remove marker from map
    map.removeLayer(poiData.marker);

    // Remove marker from currentMarkers array
    const markerIndex = currentMarkers.indexOf(poiData.marker);
    if (markerIndex > -1) {
        currentMarkers.splice(markerIndex, 1);
    }

    // Remove row from table
    poiData.row.remove();

    // Remove from starred POIs if starred
    if (poiData.starred) {
        starredPOIs.delete(poiId);
    }

    // Remove from mapping
    poiMarkerMap.delete(poiId);

    // Update POI count and download button
    updatePOICount();
    updateDownloadButtonState();

    // Refresh timeline if visible
    refreshTimelineIfVisible();
}

// ============================================
// TIMELINE FUNCTIONS
// ============================================

// Load timeline settings from localStorage
function loadTimelineSettings() {
    try {
        const saved = localStorage.getItem('timelineSettings');
        if (saved) {
            const parsed = JSON.parse(saved);
            timelineSettings = { ...timelineSettings, ...parsed };
        }
    } catch (error) {
        console.error('Error loading timeline settings:', error);
    }
    return timelineSettings;
}

// Save timeline settings to localStorage
function saveTimelineSettings() {
    try {
        localStorage.setItem('timelineSettings', JSON.stringify(timelineSettings));
    } catch (error) {
        console.error('Error saving timeline settings:', error);
    }
}

// Format elapsed time in hours to readable string
function formatElapsedTime(hours) {
    const totalMinutes = Math.round(hours * 60);
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;

    if (h === 0) {
        return `${m}min`;
    } else if (m === 0) {
        return `${h}h`;
    } else {
        return `${h}h ${m}min`;
    }
}

// Calculate appropriate tick interval based on total distance
function calculateTickInterval(totalDistance) {
    if (totalDistance <= 50) return 10;
    if (totalDistance <= 100) return 20;
    if (totalDistance <= 200) return 25;
    if (totalDistance <= 500) return 50;
    return 100;
}

// Render the elevation profile SVG
function renderElevationProfile() {
    const svg = document.getElementById('elevation-svg');
    if (!svg || elevationData.length === 0) return;

    const width = svg.clientWidth || svg.getBoundingClientRect().width;
    const height = svg.clientHeight || svg.getBoundingClientRect().height;

    if (width === 0 || height === 0) return;

    // Get elevations and find min/max
    const elevations = elevationData.map(p => p.elevation || 0);
    const minElev = Math.min(...elevations);
    const maxElev = Math.max(...elevations);
    const elevRange = maxElev - minElev || 1;

    // Downsample for performance if too many points
    let dataToRender = elevationData;
    if (elevationData.length > 500) {
        const step = Math.ceil(elevationData.length / 500);
        dataToRender = elevationData.filter((_, i) => i % step === 0);
    }

    // Generate path points
    const linePoints = dataToRender.map(p => {
        const x = (p.distance / totalRouteDistance) * width;
        const y = height - ((p.elevation - minElev) / elevRange) * (height - 10) - 5;
        return `${x},${y}`;
    }).join(' L ');

    // Generate area path (filled below the line)
    const areaPoints = dataToRender.map(p => {
        const x = (p.distance / totalRouteDistance) * width;
        const y = height - ((p.elevation - minElev) / elevRange) * (height - 10) - 5;
        return `${x},${y}`;
    });
    const areaPath = `M 0,${height} L ${areaPoints.join(' L ')} L ${width},${height} Z`;

    svg.innerHTML = `
        <path class="elevation-area" d="${areaPath}"/>
        <path class="elevation-line" d="M ${linePoints}"/>
    `;

    // Update elevation labels
    document.getElementById('elevation-max').textContent = `${Math.round(maxElev)}m`;
    document.getElementById('elevation-min').textContent = `${Math.round(minElev)}m`;
}

// Render the distance scale
function renderDistanceScale() {
    const container = document.getElementById('distance-scale');
    if (!container || totalRouteDistance === 0) return;

    const tickInterval = calculateTickInterval(totalRouteDistance);
    let html = '';

    for (let km = 0; km <= totalRouteDistance; km += tickInterval) {
        const left = (km / totalRouteDistance) * 100;
        // Use different alignment for first and last ticks to match SVG edges
        let tickClass = 'tick';
        if (left === 0) tickClass += ' tick-start';
        else if (left >= 99.9) tickClass += ' tick-end';
        html += `<div class="${tickClass}" style="left: ${left}%"><span class="tick-label">${km}</span></div>`;
    }

    // Add final tick if not already at end
    const lastTick = Math.floor(totalRouteDistance / tickInterval) * tickInterval;
    if (lastTick < totalRouteDistance - tickInterval * 0.5) {
        html += `<div class="tick tick-end" style="left: 100%"><span class="tick-label">${Math.round(totalRouteDistance)}</span></div>`;
    }

    container.innerHTML = html;
}

// Render the time scale
function renderTimeScale() {
    const container = document.getElementById('time-scale');
    if (!container || totalRouteDistance === 0) return;

    const speed = timelineSettings.speed || 25;
    const tickInterval = calculateTickInterval(totalRouteDistance);
    let html = '';

    for (let km = 0; km <= totalRouteDistance; km += tickInterval) {
        const hours = km / speed;
        const left = (km / totalRouteDistance) * 100;
        // Use different alignment for first and last ticks to match SVG edges
        let tickClass = 'tick';
        if (left === 0) tickClass += ' tick-start';
        else if (left >= 99.9) tickClass += ' tick-end';
        html += `<div class="${tickClass}" style="left: ${left}%">${formatElapsedTime(hours)}</div>`;
    }

    container.innerHTML = html;
}

// Render POI markers on the timeline
function renderPOIMarkers() {
    const container = document.getElementById('poi-markers');
    if (!container || totalRouteDistance === 0) return;

    const speed = timelineSettings.speed || 25;
    let html = '';

    // Get starred POIs and sort by distance
    const starredPOIsData = [];
    starredPOIs.forEach(poiId => {
        const poiData = poiMarkerMap.get(poiId);
        if (poiData && poiData.data) {
            starredPOIsData.push({
                id: poiId,
                ...poiData.data
            });
        }
    });

    starredPOIsData.sort((a, b) => (a.distance_on_route || 0) - (b.distance_on_route || 0));

    starredPOIsData.forEach(poi => {
        const distance = poi.distance_on_route || 0;
        const left = (distance / totalRouteDistance) * 100;
        const elapsedTime = formatElapsedTime(distance / speed);
        const iconConfig = POI_ICON_MAP[poi.poi_type] || { icon: "fa-circle", color: "#7fb800" };

        html += `
            <div class="poi-marker"
                 style="left: ${left}%"
                 data-poi-id="${poi.id}"
                 data-lat="${poi.lat}"
                 data-lon="${poi.lon}">
                <div class="poi-marker-line"></div>
                <div class="timeline-tooltip">
                    <strong>${poi.name}</strong><br>
                    ${distance.toFixed(1)} km | ${elapsedTime}
                </div>
                <i class="fas ${iconConfig.icon}" style="color: ${iconConfig.color};"></i>
            </div>
        `;
    });

    container.innerHTML = html;

    // Add click handlers for POI markers
    container.querySelectorAll('.poi-marker').forEach(el => {
        el.addEventListener('click', () => {
            const lat = parseFloat(el.dataset.lat);
            const lon = parseFloat(el.dataset.lon);
            const poiId = el.dataset.poiId;

            // Pan map to POI
            map.panTo([lat, lon]);
            map.setZoom(15);

            // Open popup if marker exists
            const poiData = poiMarkerMap.get(poiId);
            if (poiData && poiData.marker) {
                poiData.marker.openPopup();
            }
        });
    });
}

// Main function to render the entire timeline
function renderTimeline() {
    const emptyState = document.getElementById('timeline-empty');
    const content = document.getElementById('timeline-content');

    if (!emptyState || !content) return;

    // Check if we have data to show
    const hasRoute = totalRouteDistance > 0 && elevationData.length > 0;
    const hasStarredPOIs = starredPOIs.size > 0;

    if (!hasRoute) {
        emptyState.style.display = 'flex';
        content.style.display = 'none';
        emptyState.querySelector('p').textContent = 'Upload a GPX file to see the elevation profile';
        return;
    }

    if (!hasStarredPOIs) {
        emptyState.style.display = 'flex';
        content.style.display = 'none';
        emptyState.querySelector('p').textContent = 'Star POIs to see them on the timeline';
        // Still render elevation profile
    }

    // Show content
    emptyState.style.display = hasStarredPOIs ? 'none' : 'flex';
    content.style.display = 'block';

    // Render all components
    renderElevationProfile();
    renderDistanceScale();
    renderTimeScale();
    renderPOIMarkers();

    // Setup hover events for blue dot on map
    setupTimelineHoverEvents();
}

// Refresh timeline if it's currently visible
function refreshTimelineIfVisible() {
    const timelineSection = document.getElementById('timeline-section');
    if (timelineSection && timelineSection.classList.contains('visible')) {
        renderTimeline();
    }
}

// Find coordinates on route at given distance (km)
function getCoordinatesAtDistance(targetDistance) {
    if (!elevationData || elevationData.length === 0) return null;
    if (!currentRoute) return null;

    // Get route coordinates from the polyline
    const routeLatLngs = currentRoute.getLatLngs();
    if (!routeLatLngs || routeLatLngs.length === 0) return null;

    // Find the closest elevation data point to target distance
    let closestIdx = 0;
    let closestDiff = Math.abs(elevationData[0].distance - targetDistance);

    for (let i = 1; i < elevationData.length; i++) {
        const diff = Math.abs(elevationData[i].distance - targetDistance);
        if (diff < closestDiff) {
            closestDiff = diff;
            closestIdx = i;
        }
    }

    // Map to route coordinates (same index since elevation data matches route points)
    if (closestIdx < routeLatLngs.length) {
        const latLng = routeLatLngs[closestIdx];
        return [latLng.lat, latLng.lng];
    }

    return null;
}

// Show blue dot on map at given position
function showTimelineHoverMarker(lat, lng) {
    if (!timelineHoverMarker) {
        // Create the marker with a blue circle icon
        const blueIcon = L.divIcon({
            html: '<div class="timeline-hover-marker"></div>',
            className: '',
            iconSize: [14, 14],
            iconAnchor: [7, 7]
        });
        timelineHoverMarker = L.marker([lat, lng], { icon: blueIcon, interactive: false });
        timelineHoverMarker.addTo(map);
    } else {
        timelineHoverMarker.setLatLng([lat, lng]);
        if (!map.hasLayer(timelineHoverMarker)) {
            timelineHoverMarker.addTo(map);
        }
    }
}

// Hide blue dot marker
function hideTimelineHoverMarker() {
    if (timelineHoverMarker && map.hasLayer(timelineHoverMarker)) {
        map.removeLayer(timelineHoverMarker);
    }
}

// Show POI hover indicator on timeline (vertical line at POI position)
function showPOIHoverIndicator(distanceOnRoute) {
    const indicator = document.getElementById('poi-hover-indicator');
    const timelineSection = document.getElementById('timeline-section');

    if (!indicator || !timelineSection || !timelineSection.classList.contains('visible')) return;
    if (totalRouteDistance === 0) return;

    const left = (distanceOnRoute / totalRouteDistance) * 100;
    indicator.style.left = `${left}%`;
    indicator.classList.add('visible');
}

// Hide POI hover indicator
function hidePOIHoverIndicator() {
    const indicator = document.getElementById('poi-hover-indicator');
    if (indicator) {
        indicator.classList.remove('visible');
    }
}

// Setup timeline hover events (only once)
let timelineHoverEventsSetup = false;
function setupTimelineHoverEvents() {
    if (timelineHoverEventsSetup) return;

    const elevationContainer = document.querySelector('.elevation-container');
    if (!elevationContainer) return;

    elevationContainer.addEventListener('mousemove', (e) => {
        if (totalRouteDistance === 0) return;

        const rect = elevationContainer.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const percentage = Math.max(0, Math.min(1, x / rect.width));
        const distance = percentage * totalRouteDistance;

        const coords = getCoordinatesAtDistance(distance);
        if (coords) {
            showTimelineHoverMarker(coords[0], coords[1]);
        }
    });

    elevationContainer.addEventListener('mouseleave', () => {
        hideTimelineHoverMarker();
    });

    timelineHoverEventsSetup = true;
}

document.addEventListener('DOMContentLoaded', async () => {
    // Load POI icon configuration
    await loadPOIIcons();

    // Load and apply settings
    const settings = loadSettings();
    applySettings(settings);

    // Settings panel (slide-out)
    const settingsBtn = document.getElementById('settings-btn');
    const settingsPanel = document.getElementById('settings-panel');
    const settingsOverlay = document.getElementById('settings-overlay');
    const settingsClose = document.getElementById('settings-close');
    const saveSettingsBtn = document.getElementById('save-settings-btn');

    function openSettings() {
        settingsPanel.classList.add('active');
        settingsOverlay.classList.add('active');
        settingsBtn.classList.add('active');
    }

    function closeSettings() {
        settingsPanel.classList.remove('active');
        settingsOverlay.classList.remove('active');
        settingsBtn.classList.remove('active');
    }

    if (settingsBtn) {
        settingsBtn.addEventListener('click', openSettings);
    }

    if (settingsClose) {
        settingsClose.addEventListener('click', closeSettings);
    }

    if (settingsOverlay) {
        settingsOverlay.addEventListener('click', closeSettings);
    }

    // Timeline panel (floating)
    const timelineBtn = document.getElementById('timeline-btn');
    const timelineSection = document.getElementById('timeline-section');
    const timelineClose = document.getElementById('timeline-close');

    if (timelineBtn && timelineSection) {
        // Load saved timeline settings
        loadTimelineSettings();

        // Apply settings to inputs
        const speedInput = document.getElementById('timeline-speed');
        if (speedInput) speedInput.value = timelineSettings.speed;

        timelineBtn.addEventListener('click', () => {
            const isVisible = timelineSection.classList.toggle('visible');
            if (isVisible) {
                timelineBtn.classList.add('active');
                setTimeout(() => renderTimeline(), 50);
            } else {
                timelineBtn.classList.remove('active');
            }
        });
    }

    if (timelineClose) {
        timelineClose.addEventListener('click', () => {
            timelineSection.classList.remove('visible');
            timelineBtn.classList.remove('active');
        });
    }

    // Timeline speed input handler
    const timelineSpeedInput = document.getElementById('timeline-speed');
    if (timelineSpeedInput) {
        timelineSpeedInput.addEventListener('change', (e) => {
            timelineSettings.speed = Math.max(1, parseInt(e.target.value) || 25);
            e.target.value = timelineSettings.speed;
            saveTimelineSettings();
            renderTimeline();
        });
    }

    // POI panel toggle
    const poiPanel = document.getElementById('poi-panel');
    const poiPanelClose = document.getElementById('poi-panel-close');
    const togglePanelBtn = document.getElementById('toggle-panel-btn');

    if (poiPanelClose) {
        poiPanelClose.addEventListener('click', () => {
            poiPanel.classList.add('collapsed');
        });
    }

    if (togglePanelBtn) {
        togglePanelBtn.addEventListener('click', () => {
            poiPanel.classList.remove('collapsed');
        });
    }

    // Function to save settings and reload POIs
    function saveSettingsFromForm() {
        // Collect form data
        const selectedPOITypes = Array.from(document.querySelectorAll('.poi-checkbox:checked'))
            .map(checkbox => checkbox.value);

        // Validate
        if (selectedPOITypes.length === 0) {
            alert('Please select at least one POI type.');
            return false;
        }

        // Collect per-POI-type settings
        const poiSettings = {};
        let validationError = false;

        ALL_POI_TYPES.forEach(poiType => {
            const maxDevInput = document.querySelector(`.poi-max-deviation[data-poi-type="${poiType}"]`);
            const dedupInput = document.querySelector(`.poi-deduplication-radius[data-poi-type="${poiType}"]`);

            const maxDeviation = maxDevInput ? parseInt(maxDevInput.value) : 1000;
            const deduplicationRadius = dedupInput ? parseInt(dedupInput.value) : 1000;

            // Validate
            if (maxDeviation < 1) {
                alert(`Maximum deviation for ${poiType.replace(/_/g, ' ')} must be at least 1 meter.`);
                validationError = true;
                return;
            }

            if (deduplicationRadius < 1) {
                alert(`Deduplication radius for ${poiType.replace(/_/g, ' ')} must be at least 1 meter.`);
                validationError = true;
                return;
            }

            poiSettings[poiType] = {
                maxDeviation: maxDeviation,
                deduplicationRadius: deduplicationRadius
            };
        });

        if (validationError) {
            return false;
        }

        // Save settings
        const newSettings = {
            poiTypes: selectedPOITypes,
            poiSettings: poiSettings
        };
        saveSettings(newSettings);

        // Close settings panel
        closeSettings();

        // Reload POIs if route is loaded
        if (currentRouteID) {
            loadPOIs();
        }

        return true;
    }

    // Save settings button handler
    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', saveSettingsFromForm);
    }

    // Download button event listener - show format dialog
    const downloadBtn = document.getElementById('download-gpx-btn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', showDownloadFormatDialog);
    }

    // Download format dialog event listeners
    const downloadFormatModal = document.getElementById('download-format-modal');
    const downloadFormatClose = document.querySelector('.download-format-close');
    const downloadGpxBtn = document.getElementById('download-gpx-format');
    const downloadKmlBtn = document.getElementById('download-kml-format');

    if (downloadFormatClose) {
        downloadFormatClose.addEventListener('click', hideDownloadFormatDialog);
    }

    if (downloadFormatModal) {
        downloadFormatModal.addEventListener('click', (e) => {
            if (e.target === downloadFormatModal) {
                hideDownloadFormatDialog();
            }
        });
    }

    if (downloadGpxBtn) {
        downloadGpxBtn.addEventListener('click', downloadGPXFromDialog);
    }

    if (downloadKmlBtn) {
        downloadKmlBtn.addEventListener('click', downloadKMLWithStarredPOIs);
    }

    // Credits/Info modal
    const infoBtn = document.getElementById('info-btn');
    const creditsModal = document.getElementById('credits-modal');
    const creditsClose = document.getElementById('credits-close');

    function showCreditsModal() {
        if (creditsModal) {
            creditsModal.classList.add('active');
        }
    }

    function hideCreditsModal() {
        if (creditsModal) {
            creditsModal.classList.remove('active');
        }
    }

    if (infoBtn) {
        infoBtn.addEventListener('click', showCreditsModal);
    }

    if (creditsClose) {
        creditsClose.addEventListener('click', hideCreditsModal);
    }

    if (creditsModal) {
        creditsModal.addEventListener('click', (e) => {
            if (e.target === creditsModal) {
                hideCreditsModal();
            }
        });
    }
});

