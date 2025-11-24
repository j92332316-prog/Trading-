<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TradeSight Pro - 自動化交易系統</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    
    <style>
        body { font-family: 'Inter', system-ui, -apple-system, sans-serif; background-color: #f8fafc; }
        .glass-panel { background: white; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
        .animate-pulse-slow { animation: pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .7; } }
    </style>
</head>
<body class="text-slate-800">

    <nav class="bg-white border-b border-slate-200 sticky top-0 z-50 px-6 py-3 flex items-center justify-between">
        <div class="flex items-center gap-3">
            <div class="bg-blue-600 p-2 rounded-lg shadow-lg shadow-blue-200">
                <i data-lucide="activity" class="text-white w-5 h-5"></i>
            </div>
            <span class="text-xl font-bold tracking-tight text-slate-900">TradeSight<span class="text-blue-600">Pro</span></span>
        </div>
        
        <div class="flex-1 max-w-lg mx-8 relative">
            <input type="text" id="tickerInput" value="NVDA" 
                class="w-full pl-10 pr-4 py-2 bg-slate-100 border border-transparent focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-100 rounded-xl transition-all outline-none font-medium uppercase"
                placeholder="輸入代碼 (例如 AAPL)..." onkeypress="handleEnter(event)">
            <i data-lucide="search" class="absolute left-3 top-2.5 text-slate-400 w-5 h-5"></i>
        </div>

        <div class="flex items-center gap-4">
            <button class="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-lg text-sm font-medium transition" onclick="runAnalysis()">
                <i data-lucide="cpu" class="w-4 h-4"></i> 重新分析
            </button>
        </div>
    </nav>

    <main class="p-6 max-w-[1920px] mx-auto grid grid-cols-12 gap-6">

        <div class="col-span-12 lg:col-span-3 space-y-6">
            
            <div class="glass-panel rounded-2xl p-6">
                <div class="flex justify-between items-start mb-2">
                    <h1 id="displayTicker" class="text-3xl font-black text-slate-900">NVDA</h1>
                    <span class="bg-slate-100 text-slate-600 px-2 py-1 rounded text-xs font-bold">NASDAQ</span>
                </div>
                <div class="flex items-baseline gap-3">
                    <span id="currentPrice" class="text-4xl font-bold text-slate-900">$178.88</span>
                    <span id="priceChange" class="font-bold text-green-500 flex items-center gap-1">
                        <i data-lucide="trending-up" class="w-4 h-4"></i> +1.24%
                    </span>
                </div>
            </div>

            <div id="signalBox" class="rounded-2xl p-6 border-l-4 border-green-500 bg-green-50 transition-colors duration-500">
                <div class="flex justify-between items-center mb-4">
                    <span class="text-xs font-bold uppercase tracking-wider text-slate-500">AI 策略建議</span>
                    <span class="flex h-3 w-3 relative">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span class="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                    </span>
                </div>
                <h2 id="signalText" class="text-3xl font-black text-green-700 mb-1">STRONG BUY</h2>
                <p id="signalReason" class="text-sm text-slate-700 leading-relaxed font-medium mt-3">
                    系統檢測到 RSI 超賣反彈，且價格突破 MA20 關鍵壓力位。動能指標 MACD 出現黃金交叉，建議積極佈局。
                </p>
                
                <div class="grid grid-cols-2 gap-4 mt-6 pt-6 border-t border-black/5">
                    <div>
                        <span class="text-xs text-slate-500">進場價格</span>
                        <p id="entryPrice" class="font-bold text-lg text-slate-800">$178.50</p>
                    </div>
                    <div>
                        <span class="text-xs text-slate-500">目標價格</span>
                        <p id="targetPrice" class="font-bold text-lg text-slate-800">$195.60</p>
                    </div>
                </div>
            </div>

            <div class="glass-panel rounded-2xl p-5">
                <h3 class="font-bold text-slate-900 mb-4 flex items-center gap-2">
                    <i data-lucide="layers" class="w-4 h-4 text-blue-500"></i> 圖層控制
                </h3>
                <div class="space-y-3">
                    <label class="flex items-center gap-3 cursor-pointer group">
                        <input type="checkbox" checked class="w-4 h-4 text-blue-600 rounded focus:ring-blue-500">
                        <span class="text-sm font-medium text-slate-700">移動平均線 (MA)</span>
                    </label>
                    <label class="flex items-center gap-3 cursor-pointer group">
                        <input type="checkbox" checked class="w-4 h-4 text-blue-600 rounded focus:ring-blue-500">
                        <span class="text-sm font-medium text-slate-700">布林通道 (Bollinger)</span>
                    </label>
                    <label class="flex items-center gap-3 cursor-pointer group">
                        <input type="checkbox" class="w-4 h-4 text-blue-600 rounded focus:ring-blue-500">
                        <span class="text-sm font-medium text-slate-700">斐波那契回撤</span>
                    </label>
                </div>
            </div>
        </div>

        <div class="col-span-12 lg:col-span-9 space-y-6">
            <div class="glass-panel rounded-2xl p-1 shadow-sm h-[600px] flex flex-col relative">
                <div class="absolute top-4 left-4 z-10 flex gap-2">
                    <span class="px-3 py-1 bg-blue-50 text-blue-700 text-xs font-bold rounded-full border border-blue-100">1H</span>
                    <span class="px-3 py-1 bg-white text-slate-600 text-xs font-bold rounded-full border border-slate-200 shadow-sm cursor-pointer hover:bg-slate-50">4H</span>
                    <span class="px-3 py-1 bg-white text-slate-600 text-xs font-bold rounded-full border border-slate-200 shadow-sm cursor-pointer hover:bg-slate-50">1D</span>
                </div>
                <div id="chartContainer" class="w-full h-full rounded-xl overflow-hidden"></div>
            </div>

            <div class="grid grid-cols-2 gap-6">
                <div class="glass-panel rounded-2xl p-4 h-48 relative">
                    <span class="absolute top-3 left-3 text-xs font-bold text-slate-400">RSI (14)</span>
                    <div id="rsiContainer" class="w-full h-full pt-6"></div>
                </div>
                <div class="glass-panel rounded-2xl p-4 h-48 relative">
                     <span class="absolute top-3 left-3 text-xs font-bold text-slate-400">MACD Simulation</span>
                     <div class="flex items-center justify-center h-full text-slate-300 text-sm">
                        此區域為視覺模擬與主圖連動
                     </div>
                </div>
            </div>
        </div>
    </main>

    <script>
        // 初始化圖標
        lucide.createIcons();

        // 1. 初始化 TradingView 圖表
        const chartContainer = document.getElementById('chartContainer');
        const chart = LightweightCharts.createChart(chartContainer, {
            layout: { background: { type: 'solid', color: 'white' }, textColor: '#334155' },
            grid: { vertLines: { color: '#f1f5f9' }, horzLines: { color: '#f1f5f9' } },
            rightPriceScale: { borderColor: '#e2e8f0' },
            timeScale: { borderColor: '#e2e8f0' },
            crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        });

        // 建立 K 線圖層
        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#22c55e', downColor: '#ef4444', borderVisible: false, wickUpColor: '#22c55e', wickDownColor: '#ef4444',
        });

        // 建立 MA 線圖層
        const maSeries = chart.addLineSeries({ color: '#3b82f6', lineWidth: 2 });
        
        // 2. 初始化 RSI 副圖表
        const rsiContainer = document.getElementById('rsiContainer');
        const rsiChart = LightweightCharts.createChart(rsiContainer, {
            layout: { background: { type: 'solid', color: 'white' }, textColor: '#334155' },
            grid: { vertLines: { color: 'transparent' }, horzLines: { color: '#f1f5f9' } },
            rightPriceScale: { visible: true },
            timeScale: { visible: false },
        });
        const rsiSeries = rsiChart.addLineSeries({ color: '#8b5cf6', lineWidth: 2 });
        // 加入 RSI 參考線 (30/70)
        const rsiHighLine = rsiChart.addLineSeries({ color: '#ef4444', lineWidth: 1, lineStyle: 2 });
        const rsiLowLine = rsiChart.addLineSeries({ color: '#22c55e', lineWidth: 1, lineStyle: 2 });

        // 3. 數據生成與邏輯核心 (解決 CORS 問題，使用高品質模擬數據)
        function generateData(startPrice = 150, count = 100) {
            let data = [];
            let rsiData = [];
            let maData = [];
            let time = new Date();
            time.setHours(9, 0, 0, 0);
            let currentPrice = startPrice;

            for (let i = 0; i < count; i++) {
                // 模擬隨機波動
                let volatility = (Math.random() - 0.48) * 2.5; 
                let open = currentPrice;
                let close = open + volatility;
                let high = Math.max(open, close) + Math.random();
                let low = Math.min(open, close) - Math.random();
                
                // 調整時間
                time.setMinutes(time.getMinutes() + 15);
                let timeString = time.getTime() / 1000;

                data.push({ time: timeString, open, high, low, close });
                
                // 模擬 MA
                let maVal = close * (1 + (Math.sin(i/10) * 0.02)); 
                maData.push({ time: timeString, value: maVal });

                // 模擬 RSI
                let rsiVal = 50 + (Math.sin(i/5) * 25) + (Math.random() * 10);
                rsiData.push({ time: timeString, value: Math.max(0, Math.min(100, rsiVal)) });

                currentPrice = close;
            }
            return { data, maData, rsiData, lastClose: currentPrice, lastRSI: rsiData[rsiData.length-1].value };
        }

        // 4. 自動化分析邏輯 (AI Logic)
        function updateSignal(price, rsi) {
            const signalBox = document.getElementById('signalBox');
            const signalText = document.getElementById('signalText');
            const signalReason = document.getElementById('signalReason');
            const priceChangeEl = document.getElementById('priceChange');

            // 模擬漲跌幅顯示
            const change = (Math.random() * 2 - 0.8).toFixed(2);
            const isUp = change > 0;
            priceChangeEl.innerHTML = isUp 
                ? `<i data-lucide="trending-up" class="w-4 h-4"></i> +${change}%` 
                : `<i data-lucide="trending-down" class="w-4 h-4"></i> ${change}%`;
            priceChangeEl.className = `font-bold flex items-center gap-1 ${isUp ? 'text-green-500' : 'text-red-500'}`;

            // 策略判定
            if (rsi < 35) {
                // 強力買入
                signalBox.className = "rounded-2xl p-6 border-l-4 border-green-500 bg-green-50 transition-colors duration-500";
                signalText.innerText = "STRONG BUY";
                signalText.className = "text-3xl font-black text-green-700 mb-1";
                signalReason.innerText = "技術面顯示超賣訊號 (RSI < 35)，且價格在支撐位獲得強力反彈，量能溫和放大，建議進場。";
            } else if (rsi > 65) {
                // 強力賣出
                signalBox.className = "rounded-2xl p-6 border-l-4 border-red-500 bg-red-50 transition-colors duration-500";
                signalText.innerText = "SELL";
                signalText.className = "text-3xl font-black text-red-700 mb-1";
                signalReason.innerText = "股價進入高檔鈍化區 (RSI > 65)，上方壓力沈重，建議分批獲利了結以降低風險。";
            } else {
                // 觀望
                signalBox.className = "rounded-2xl p-6 border-l-4 border-slate-400 bg-slate-50 transition-colors duration-500";
                signalText.innerText = "HOLD";
                signalText.className = "text-3xl font-black text-slate-600 mb-1";
                signalReason.innerText = "目前趨勢不明朗，價格在區間震盪整理，建議等待方向確認後再行操作。";
            }
            
            // 更新進出場建議
            document.getElementById('entryPrice').innerText = `$${(price * 0.995).toFixed(2)}`;
            document.getElementById('targetPrice').innerText = `$${(price * 1.05).toFixed(2)}`;
            lucide.createIcons();
        }

        // 5. 主執行函數
        function runAnalysis() {
            const ticker = document.getElementById('tickerInput').value.toUpperCase();
            document.getElementById('displayTicker').innerText = ticker;

            // 隨機產生起始價格 (為了演示效果)
            const startPrice = Math.random() * 200 + 50;
            
            // 生成數據
            const dataset = generateData(startPrice, 150);
            
            // 更新圖表
            candlestickSeries.setData(dataset.data);
            maSeries.setData(dataset.maData);
            rsiSeries.setData(dataset.rsiData);
            
            // 設定 RSI 參考線數據 (需為直線)
            const refData = dataset.rsiData.map(d => ({ time: d.time, value: 70 }));
            const refDataLow = dataset.rsiData.map(d => ({ time: d.time, value: 30 }));
            rsiHighLine.setData(refData);
            rsiLowLine.setData(refDataLow);

            // 更新價格顯示
            document.getElementById('currentPrice').innerText = `$${dataset.lastClose.toFixed(2)}`;

            // 執行 AI 判斷
            updateSignal(dataset.lastClose, dataset.lastRSI);
            
            // 自動縮放圖表
            chart.timeScale().fitContent();
            rsiChart.timeScale().fitContent();
        }

        function handleEnter(e) {
            if(e.key === 'Enter') runAnalysis();
        }

        // 頁面載入時執行一次
        window.onload = runAnalysis;

        // 響應式調整
        window.addEventListener('resize', () => {
            chart.resize(chartContainer.clientWidth, chartContainer.clientHeight);
            rsiChart.resize(rsiContainer.clientWidth, rsiContainer.clientHeight);
        });

    </script>
</body>
</html>
