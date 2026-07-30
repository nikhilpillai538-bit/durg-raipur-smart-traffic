 <!DOCTYPE html> 

<html class="light" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>UrbanFlow | Civic Flow Smart Corridor</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script id="tailwind-config">
      tailwind.config = {
        darkMode: "class",
        theme: {
          extend: {
            "colors": {
                    "surface-dim": "#d8dae2",
                    "on-tertiary-container": "#ffdfcc",
                    "primary-container": "#1565c0",
                    "background": "#f9f9ff",
                    "surface-container-lowest": "#ffffff",
                    "primary": "#1565c0",
                    "on-surface-variant": "#424752",
                    "secondary-fixed": "#a3f69c",
                    "outline-variant": "#c2c6d4",
                    "secondary-fixed-dim": "#88d982",
                    "on-primary-fixed-variant": "#00468c",
                    "on-primary-container": "#dae5ff",
                    "on-tertiary-fixed-variant": "#723600",
                    "surface-container": "#ecedf6",
                    "surface-bright": "#f9f9ff",
                    "surface-tint": "#005db7",
                    "on-primary": "#ffffff",
                    "tertiary-container": "#a15000",
                    "surface-variant": "#e1e2ea",
                    "surface-container-low": "#f2f3fb",
                    "inverse-on-surface": "#eff0f9",
                    "on-secondary-fixed": "#002204",
                    "inverse-surface": "#2e3037",
                    "tertiary-fixed-dim": "#ffb786",
                    "on-surface": "#1a1a1a",
                    "surface": "#f9f9ff",
                    "on-tertiary": "#ffffff",
                    "error": "#ba1a1a",
                    "on-background": "#1a1a1a",
                    "surface-container-high": "#e7e8f0",
                    "on-secondary-fixed-variant": "#005312",
                    "on-tertiary-fixed": "#311300",
                    "tertiary-fixed": "#ffdcc6",
                    "tertiary": "#7d3c00",
                    "secondary-container": "#a0f399",
                    "secondary": "#1b6d24",
                    "outline": "#e5e7eb",
                    "inverse-primary": "#a9c7ff",
                    "primary-fixed": "#d6e3ff",
                    "on-error-container": "#93000a",
                    "on-error": "#ffffff",
                    "on-secondary-container": "#217128",
                    "primary-fixed-dim": "#a9c7ff",
                    "surface-container-highest": "#e1e2ea",
                    "on-secondary": "#ffffff",
                    "error-container": "#ffdad6",
                    "on-primary-fixed": "#001b3d"
            },
            "borderRadius": {
                    "DEFAULT": "0.125rem",
                    "lg": "0.25rem",
                    "xl": "0.5rem",
                    "full": "0.75rem"
            },
            "spacing": {
                    "sm": "12px",
                    "md": "24px",
                    "lg": "40px",
                    "xl": "64px",
                    "gutter": "16px",
                    "margin-desktop": "32px",
                    "margin-mobile": "16px",
                    "xs": "4px",
                    "base": "8px"
            },
            "fontFamily": {
                    "stats-display": ["Inter"],
                    "headline-sm": ["Inter"],
                    "body-md": ["Inter"],
                    "label-md": ["Inter"],
                    "headline-md": ["Inter"],
                    "headline-lg": ["Inter"],
                    "body-lg": ["Inter"],
                    "headline-lg-mobile": ["Inter"],
                    "body-sm": ["Inter"]
            }
          },
        },
      }
    </script>
<style>
        body { font-family: 'Inter', sans-serif; -webkit-font-smoothing: antialiased; }
        .streamlit-sidebar { width: 300px; min-width: 300px; }
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 10px; }
        .tab-active { border-bottom: 2px solid #1565c0; color: #1565c0; font-weight: 600; }
        input[type="range"] { -webkit-appearance: none; appearance: none; background: #e5e7eb; height: 6px; border-radius: 3px; }
        input[type="range"]::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 18px; height: 18px; background: #1565c0; cursor: pointer; border-radius: 50%; border: 2px solid white; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
    </style>
</head>
<body class="bg-background flex h-screen overflow-hidden text-on-surface">
<!-- Streamlit Style Sidebar -->
<aside class="streamlit-sidebar bg-surface-container-low border-r border-outline flex flex-col h-full overflow-y-auto custom-scrollbar p-6">
<div class="mb-10">
<h1 class="text-xl font-bold tracking-tight text-on-background">URBANFLOW</h1>
<p class="text-[10px] uppercase tracking-widest text-on-surface-variant mt-1 font-semibold">Smart Corridor v2.4</p>
</div>
<div class="space-y-8">
<section>
<h2 class="text-sm font-bold text-on-surface mb-5 uppercase tracking-wider">Corridor Controls</h2>
<div class="space-y-6">
<div>
<label class="block text-xs font-bold text-on-surface-variant uppercase mb-2">Transit Origin</label>
<select class="w-full bg-white border border-outline rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all">
<option>Durg Junction</option>
<option>Bhilai Nagar</option>
<option>Raipur Central</option>
</select>
</div>
<div>
<label class="block text-xs font-bold text-on-surface-variant uppercase mb-2">Transit Destination</label>
<select class="w-full bg-white border border-outline rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all">
<option>Raipur Airport (RPR)</option>
<option>AIIMS Raipur</option>
<option>Magneto Mall</option>
</select>
</div>
<div>
<div class="flex justify-between mb-2">
<label class="text-xs font-bold text-on-surface-variant uppercase">Hour of Day</label>
<span class="text-xs font-bold text-primary" id="hourLabel">14:00</span>
</div>
<input class="w-full cursor-pointer" max="23" min="0" oninput="document.getElementById('hourLabel').innerText = this.value.padStart(2, '0') + ':00'" type="range" value="14"/>
</div>
<div>
<label class="block text-xs font-bold text-on-surface-variant uppercase mb-3">Operational Day</label>
<div class="space-y-3">
<label class="flex items-center gap-3 cursor-pointer group">
<input checked="" class="text-primary focus:ring-primary h-4 w-4 border-outline" name="day" type="radio"/>
<span class="text-sm font-medium group-hover:text-primary transition-colors">Weekday (Mon-Fri)</span>
</label>
<label class="flex items-center gap-3 cursor-pointer group">
<input class="text-primary focus:ring-primary h-4 w-4 border-outline" name="day" type="radio"/>
<span class="text-sm font-medium group-hover:text-primary transition-colors">Weekend / Holiday</span>
</label>
</div>
</div>
</div>
</section>
<section class="pt-8 border-t border-outline">
<button class="w-full bg-primary text-white py-3 rounded-lg text-sm font-bold hover:bg-blue-700 transition-all flex items-center justify-center gap-2 shadow-sm">
<span class="material-symbols-outlined text-sm">refresh</span>
                Apply Simulations
            </button>
</section>
</div>
<div class="mt-auto pt-8 flex items-center gap-3 opacity-60">
<div class="w-8 h-8 rounded-full bg-surface-container flex items-center justify-center">
<span class="material-symbols-outlined text-sm text-on-surface">analytics</span>
</div>
<div class="text-[10px] uppercase font-bold tracking-widest text-on-surface-variant">
            System Engine v2.4r
        </div>
</div>
</aside>
<!-- Main Content Area -->
<main class="flex-1 flex flex-col h-screen overflow-y-auto custom-scrollbar">
<!-- Header -->
<header class="px-8 pt-10 pb-8 border-b border-outline bg-white">
<div class="flex items-end justify-between max-w-7xl mx-auto w-full">
<div>
<h2 class="text-3xl font-bold text-on-background tracking-tight">Durg-Raipur Corridor</h2>
<p class="text-sm text-on-surface-variant mt-1.5 flex items-center gap-2">
<span class="w-2 h-2 rounded-full bg-green-500"></span>
                    NH-49 / GE Road Real-time Analytics
                </p>
</div>
<div class="flex gap-3">
<button class="px-5 py-2 border border-outline rounded-lg text-xs font-bold uppercase tracking-wider text-on-surface-variant hover:bg-surface-container-low transition-colors">Sync System</button>
<button class="px-5 py-2 bg-error text-white rounded-lg text-xs font-bold uppercase tracking-wider hover:opacity-90 shadow-sm">Issue Alert</button>
</div>
</div>
</header>
<div class="px-8 py-8 space-y-8 max-w-7xl mx-auto w-full">
<!-- Top Metrics Row -->
<div class="grid grid-cols-1 md:grid-cols-4 gap-6">
<div class="bg-white border border-outline p-6 rounded-xl shadow-sm">
<p class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-3">Live Travel Time</p>
<div class="flex items-baseline gap-2">
<span class="text-4xl font-bold text-on-background">52m</span>
<span class="text-xs text-green-600 font-bold">-4m avg</span>
</div>
</div>
<div class="bg-white border border-outline p-6 rounded-xl shadow-sm">
<p class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-3">Congestion Index</p>
<div class="flex items-baseline gap-2">
<span class="text-4xl font-bold text-on-background">34%</span>
<span class="text-[10px] bg-yellow-100 text-yellow-800 px-2 py-1 rounded font-bold uppercase ml-1">Moderate</span>
</div>
</div>
<div class="bg-white border border-outline p-6 rounded-xl shadow-sm">
<p class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-3">System Status</p>
<div class="flex items-baseline">
<span class="text-2xl font-bold uppercase text-on-background tracking-tight">Operational</span>
</div>
</div>
<div class="bg-white border border-outline p-6 rounded-xl shadow-sm">
<p class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-3">Avg. Parking Openings</p>
<div class="flex items-baseline gap-2">
<span class="text-4xl font-bold text-on-background">680</span>
<span class="text-xs text-on-surface-variant font-medium">Slots Avail.</span>
</div>
</div>
</div>
<!-- Environmental Expander -->
<details class="group bg-white border border-outline rounded-xl overflow-hidden transition-all shadow-sm" open="">
<summary class="flex items-center justify-between px-6 py-4 cursor-pointer hover:bg-surface-container-low list-none">
<span class="text-sm font-bold flex items-center gap-3 text-on-background">
<span class="material-symbols-outlined text-primary group-open:rotate-180 transition-transform">expand_more</span>
                    Environmental &amp; Delay Impact Metrics
                </span>
<span class="text-xs text-on-surface-variant font-medium">View carbon footprint and efficiency data</span>
</summary>
<div class="px-10 py-8 border-t border-outline grid grid-cols-1 md:grid-cols-3 gap-12">
<div>
<div class="flex justify-between text-[10px] font-bold uppercase text-on-surface-variant mb-3">
<span>Fuel Inefficiency</span>
<span class="text-on-background">1.4L / Day</span>
</div>
<div class="w-full bg-surface-container h-2 rounded-full overflow-hidden">
<div class="bg-primary h-full w-[45%]"></div>
</div>
</div>
<div>
<div class="flex justify-between text-[10px] font-bold uppercase text-on-surface-variant mb-3">
<span>Carbon Displacement</span>
<span class="text-on-background">3.2kg CO2</span>
</div>
<div class="w-full bg-surface-container h-2 rounded-full overflow-hidden">
<div class="bg-primary h-full w-[70%]"></div>
</div>
</div>
<div>
<div class="flex justify-between text-[10px] font-bold uppercase text-on-surface-variant mb-3">
<span>Time Variance</span>
<span class="text-on-background">1.2x Delay</span>
</div>
<div class="w-full bg-surface-container h-2 rounded-full overflow-hidden">
<div class="bg-primary h-full w-[25%]"></div>
</div>
</div>
</div>
</details>
<!-- Main Content Tabs -->
<div>
<div class="flex border-b border-outline mb-8 overflow-x-auto">
<button class="px-8 py-4 text-sm tab-active whitespace-nowrap" onclick="showTab('map')">Live Corridor Map</button>
<button class="px-8 py-4 text-sm text-on-surface-variant hover:text-primary transition-colors whitespace-nowrap" onclick="showTab('forecast')">Traffic Predictions</button>
<button class="px-8 py-4 text-sm text-on-surface-variant hover:text-primary transition-colors whitespace-nowrap" onclick="showTab('parking')">Parking Availability</button>
</div>
<!-- Tab Content: Map -->
<div class="block" id="tab-map">
<div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
<div class="lg:col-span-3 border border-outline rounded-xl overflow-hidden bg-white relative shadow-sm min-h-[500px]">
<div class="absolute inset-0 grayscale opacity-80 contrast-125" style="background-image: url('https://lh3.googleusercontent.com/aida-public/AB6AXuBbNXIl5TDS8kOfTGX8_R2EYsYO0Edk0okJ0GAv13yV3BoXLFm1PHsQdkPMxU3RSLCG8hTb84qqa-yRZ6JTOc1SLw5cRFS5S3qWdQM4DZ-VKDUnMeXxE43_jXNEbRbtd0zkl5PmJjA2KHFYuNXCkorxaJmVxRZBrT1RZGic04vxoAhHdH9_myk4rN5dZPhAmMqIdmB6TfaJJksLaG2bcnbzHw0ty2X-mp5E4-6F7k3PwrOKr-4wPTntKA'); background-size: cover; background-position: center;"></div>
<div class="absolute top-6 right-6 bg-white/95 backdrop-blur-md p-4 rounded-lg border border-outline flex gap-6 text-[10px] font-bold uppercase shadow-lg">
<span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-red-600"></span> High</span>
<span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-yellow-500"></span> Med</span>
<span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-green-500"></span> Low</span>
</div>
<div class="absolute bottom-8 left-8 p-5 bg-white border-l-4 border-primary shadow-xl max-w-sm rounded-r-lg">
<div class="flex items-center gap-2 mb-2">
<span class="material-symbols-outlined text-primary text-lg">warning</span>
<p class="text-[10px] font-bold uppercase text-primary tracking-widest">Recommendation Alert</p>
</div>
<p class="text-sm font-semibold text-on-background">Slow traffic near Tatibandh Sector due to maintenance. Consider taking Sarona bypass to save 8 mins.</p>
</div>
</div>
<div class="lg:col-span-1 space-y-6">
<div class="bg-white border border-outline rounded-xl p-6 shadow-sm">
<h4 class="text-xs font-bold uppercase text-on-surface-variant tracking-wider mb-4">Route Details</h4>
<div class="space-y-4">
<div class="flex items-start gap-3">
<span class="material-symbols-outlined text-sm mt-1 text-primary">trip_origin</span>
<div>
<p class="text-[10px] font-bold text-on-surface-variant uppercase">Origin</p>
<p class="text-sm font-semibold">Durg Junction</p>
</div>
</div>
<div class="w-px h-6 bg-outline ml-1.5"></div>
<div class="flex items-start gap-3">
<span class="material-symbols-outlined text-sm mt-1 text-primary">location_on</span>
<div>
<p class="text-[10px] font-bold text-on-surface-variant uppercase">Destination</p>
<p class="text-sm font-semibold">Raipur Airport</p>
</div>
</div>
<div class="pt-4 border-t border-outline">
<p class="text-[10px] font-bold text-on-surface-variant uppercase mb-1">Estimated Distance</p>
<p class="text-lg font-bold">38.4 KM</p>
</div>
</div>
</div>
<div class="bg-primary/5 border border-primary/10 rounded-xl p-6">
<p class="text-xs font-bold text-primary uppercase tracking-widest mb-2">Pro Tip</p>
<p class="text-xs leading-relaxed text-on-surface-variant">Public transit is 15% faster during this window. Local shuttle available every 12 mins.</p>
</div>
</div>
</div>
</div>
<!-- Tab Content: Forecast -->
<div class="hidden" id="tab-forecast">
<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
<div class="lg:col-span-2 border border-outline rounded-xl p-8 bg-white shadow-sm">
<div class="flex justify-between items-center mb-10">
<h3 class="text-sm font-bold uppercase tracking-widest text-on-background">24h Volume Forecast</h3>
<div class="flex gap-4">
<span class="flex items-center gap-2 text-[10px] font-bold uppercase text-on-surface-variant">
<span class="w-3 h-3 rounded-sm bg-primary"></span> Predicted
                                </span>
<span class="flex items-center gap-2 text-[10px] font-bold uppercase text-on-surface-variant">
<span class="w-3 h-3 rounded-sm bg-surface-container"></span> Historical
                                </span>
</div>
</div>
<div class="h-64 flex items-end justify-between gap-3 px-4">
<div class="w-full bg-surface-container hover:bg-primary/40 transition-all rounded-t" style="height: 35%"></div>
<div class="w-full bg-surface-container hover:bg-primary/40 transition-all rounded-t" style="height: 25%"></div>
<div class="w-full bg-surface-container hover:bg-primary/40 transition-all rounded-t" style="height: 30%"></div>
<div class="w-full bg-primary rounded-t shadow-inner" style="height: 85%"></div>
<div class="w-full bg-surface-container hover:bg-primary/40 transition-all rounded-t" style="height: 65%"></div>
<div class="w-full bg-surface-container hover:bg-primary/40 transition-all rounded-t" style="height: 55%"></div>
<div class="w-full bg-primary rounded-t shadow-inner" style="height: 95%"></div>
<div class="w-full bg-surface-container hover:bg-primary/40 transition-all rounded-t" style="height: 75%"></div>
<div class="w-full bg-surface-container hover:bg-primary/40 transition-all rounded-t" style="height: 50%"></div>
<div class="w-full bg-surface-container hover:bg-primary/40 transition-all rounded-t" style="height: 40%"></div>
</div>
<div class="flex justify-between text-[10px] text-on-surface-variant mt-8 px-4 font-bold uppercase tracking-widest">
<span>00:00</span>
<span>06:00</span>
<span>12:00</span>
<span>18:00</span>
<span>23:59</span>
</div>
</div>
<div class="space-y-6">
<div class="bg-primary text-white border border-primary rounded-xl p-8 shadow-lg">
<h4 class="text-xs font-bold uppercase tracking-widest mb-6 opacity-80">Best Time to Leave</h4>
<div class="flex items-center gap-4 mb-4">
<span class="material-symbols-outlined text-3xl">schedule</span>
<div>
<p class="text-2xl font-bold">10:15 AM</p>
<p class="text-[10px] font-bold uppercase opacity-80 tracking-widest">Target Departure</p>
</div>
</div>
<p class="text-xs leading-relaxed opacity-90 mt-4 border-t border-white/20 pt-4">Leaving at this time saves approximately 18 minutes of idle time compared to the peak rush hour.</p>
</div>
<div class="bg-white border border-outline rounded-xl p-6 shadow-sm">
<h4 class="text-xs font-bold uppercase text-on-surface-variant tracking-wider mb-4">Traffic Insights</h4>
<ul class="space-y-4">
<li class="flex gap-3">
<span class="w-1.5 h-1.5 rounded-full bg-red-500 mt-1.5 shrink-0"></span>
<p class="text-xs">Peak congestion expected between 05:00 PM and 07:00 PM.</p>
</li>
<li class="flex gap-3">
<span class="w-1.5 h-1.5 rounded-full bg-green-500 mt-1.5 shrink-0"></span>
<p class="text-xs">Traffic flow is 20% lighter than average for a Tuesday.</p>
</li>
</ul>
</div>
</div>
</div>
</div>
<!-- Tab Content: Parking -->
<div class="hidden" id="tab-parking">
<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
<div class="lg:col-span-2 border border-outline rounded-xl overflow-hidden bg-white shadow-sm">
<table class="w-full text-left text-sm">
<thead class="bg-surface-container-low border-b border-outline">
<tr>
<th class="px-8 py-5 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Facility</th>
<th class="px-8 py-5 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Availability</th>
<th class="px-8 py-5 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Status</th>
</tr>
</thead>
<tbody class="divide-y divide-outline">
<tr class="hover:bg-surface-container-low transition-colors">
<td class="px-8 py-6">
<p class="font-bold text-on-background">Bhilai Transit Hub</p>
<p class="text-[10px] text-on-surface-variant">Zone A &amp; B</p>
</td>
<td class="px-8 py-6">
<span class="font-bold text-on-background">142 / 200</span>
<div class="w-32 bg-surface-container h-1.5 rounded-full mt-2 overflow-hidden">
<div class="bg-green-500 h-full w-[71%]"></div>
</div>
</td>
<td class="px-8 py-6"><span class="text-green-600 font-bold uppercase text-[10px] bg-green-50 px-2 py-1 rounded">Optimal</span></td>
</tr>
<tr class="hover:bg-surface-container-low transition-colors">
<td class="px-8 py-6">
<p class="font-bold text-on-background">Raipur Central Plaza</p>
<p class="text-[10px] text-on-surface-variant">Underground Levels 1-3</p>
</td>
<td class="px-8 py-6">
<span class="font-bold text-on-background">12 / 350</span>
<div class="w-32 bg-surface-container h-1.5 rounded-full mt-2 overflow-hidden">
<div class="bg-red-500 h-full w-[96%]"></div>
</div>
</td>
<td class="px-8 py-6"><span class="text-red-600 font-bold uppercase text-[10px] bg-red-50 px-2 py-1 rounded">Critical</span></td>
</tr>
<tr class="hover:bg-surface-container-low transition-colors">
<td class="px-8 py-6">
<p class="font-bold text-on-background">Tatibandh Park &amp; Ride</p>
<p class="text-[10px] text-on-surface-variant">Main Entrance Lot</p>
</td>
<td class="px-8 py-6">
<span class="font-bold text-on-background">526 / 600</span>
<div class="w-32 bg-surface-container h-1.5 rounded-full mt-2 overflow-hidden">
<div class="bg-green-500 h-full w-[12%]"></div>
</div>
</td>
<td class="px-8 py-6"><span class="text-green-600 font-bold uppercase text-[10px] bg-green-50 px-2 py-1 rounded">Wide Open</span></td>
</tr>
</tbody>
</table>
</div>
<div class="space-y-6">
<div class="bg-white border border-outline rounded-xl p-8 shadow-sm">
<h4 class="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-6">Occupancy Forecast</h4>
<div class="space-y-6">
<div>
<div class="flex justify-between text-[10px] font-bold uppercase mb-2">
<span>Next 1 hour</span>
<span class="text-red-600">+15% inflow</span>
</div>
<p class="text-xs text-on-surface-variant leading-relaxed">Raipur Central likely to hit full capacity by 15:30. Recommend diversion to Railway Station Annex.</p>
</div>
<div class="p-4 bg-surface-container-low rounded-lg border border-outline">
<div class="flex items-center gap-3 mb-2">
<span class="material-symbols-outlined text-primary">info</span>
<span class="text-[10px] font-bold uppercase tracking-widest">Smart Suggestion</span>
</div>
<p class="text-xs leading-relaxed text-on-surface-variant">Pre-booking available for Bhilai Hub. Save 10% on parking fees via the UrbanFlow app.</p>
</div>
</div>
</div>
</div>
</div>
</div>
</div>
</div>
</main>
<script>
    function showTab(tabId) {
        // Toggle tabs
        ['map', 'forecast', 'parking'].forEach(id => {
            const el = document.getElementById('tab-' + id);
            const btn = document.querySelector(`button[onclick="showTab('${id}')"]`);
            if (id === tabId) {
                el.classList.remove('hidden');
                btn.classList.add('tab-active');
                btn.classList.remove('text-on-surface-variant');
            } else {
                el.classList.add('hidden');
                btn.classList.remove('tab-active');
                btn.classList.add('text-on-surface-variant');
            }
        });
    }

    // Initialize button effects
    document.querySelectorAll('button').forEach(btn => {
        if (btn.innerText.toLowerCase().includes('sync') || btn.innerText.toLowerCase().includes('apply')) {
            btn.addEventListener('click', function() {
                const originalText = this.innerHTML;
                this.innerHTML = '<span class="material-symbols-outlined text-sm animate-spin">sync</span> <span class="ml-2">Processing...</span>';
                this.style.opacity = '0.7';
                this.disabled = true;
                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.style.opacity = '1';
                    this.disabled = false;
                }, 1000);
            });
        }
    });
</script>
</body></html>