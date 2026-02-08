import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup

# --- 1. 專業級頁面配置 ---
st.set_page_config(page_title="Ultra AI Investment Terminal", layout="wide", page_icon="📈")

# 自定義 CSS 讓介面更緊湊專業
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .st-emotion-cache-1y4p8pa {
        padding-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("📈 Ultra AI 量化投資終端機")
st.markdown("---")

# --- 2. 側邊欄：戰情控制室 ---
st.sidebar.header("🕹️ 戰情控制室")
ticker = st.sidebar.text_input("主標的代碼 (台股請加 .TW)", value="0050.TW")
timeframe = st.sidebar.selectbox("觀測週期", ['3mo', '6mo', '1y', '3y', '5y', 'max'], index=2)

st.sidebar.markdown("### ⚔️ 績效對決")
compare_tickers = st.sidebar.multiselect(
    "選擇對照組 (Benchmark)",
    options=["2330.TW", "2317.TW", "2454.TW", "0056.TW", "00878.TW", "^TWII", "VOO", "NVDA", "AAPL"],
    default=["^TWII"] # 預設對比大盤
)

st.sidebar.markdown("### 🛠️ 技術指標疊加")
show_ma = st.sidebar.checkbox("SMA 均線 (20/60日)", value=True)
indicator = st.sidebar.selectbox("主圖指標", ["無", "布林通道 (Bollinger)"])
oscillator = st.sidebar.selectbox("副圖指標", ["成交量", "MACD (趨勢)", "RSI (強弱)"], index=1)

# --- 3. 核心數據引擎 (加入快取與錯誤處理) ---
@st.cache_data(ttl=3600)
def get_stock_data(symbol, period):
    try:
        df = yf.download(symbol, period=period)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # 計算基礎技術指標
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['Returns'] = df['Close'].pct_change()
        return df
    except:
        return None

def get_normalized_data(tickers, period):
    """將多檔股票歸一化 (起點設為 0%) 進行比較"""
    data_dict = {}
    for t in tickers:
        df = yf.download(t, period=period)['Close']
        if not df.empty:
            if isinstance(df, pd.DataFrame): df = df.iloc[:, 0]
            # (當前價格 - 初始價格) / 初始價格
            normalized = ((df - df.iloc[0]) / df.iloc[0]) * 100
            data_dict[t] = normalized
    return pd.DataFrame(data_dict)

# 執行數據抓取
main_df = get_stock_data(ticker, timeframe)

# --- 4. 主程式邏輯 ---
if main_df is not None and not main_df.empty:
    
    # --- 頂部：即時行情與 AI 訊號 ---
    curr_price = float(main_df['Close'].iloc[-1])
    prev_price = float(main_df['Close'].iloc[-2])
    chg = curr_price - prev_price
    pct_chg = (chg / prev_price) * 100
    
    # 計算簡單信號
    ma20 = main_df['MA20'].iloc[-1]
    trend_signal = "🐂 多頭格局" if curr_price > ma20 else "🐻 空頭整理"
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"{ticker} 現價", f"${curr_price:,.2f}", f"{pct_chg:.2f}%")
    c2.metric("趨勢訊號", trend_signal, f"MA20: {ma20:.1f}")
    c3.metric("成交量", f"{main_df['Volume'].iloc[-1]:,.0f}")
    
    # 計算波動率 (風險指標)
    volatility = main_df['Returns'].std() * (252 ** 0.5) * 100
    c4.metric("年化波動率 (風險)", f"{volatility:.1f}%", delta_color="off")

    # --- 頁面分頁系統 ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 深度技術分析", 
        "🛡️ 風險與基本面", 
        "💰 財富模擬艙", 
        "📰 AI 情緒雷達"
    ])

    # === Tab 1: 技術分析 (Pro Charts) ===
    with tab1:
        # 1. K線主圖
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=main_df.index,
                open=main_df['Open'], high=main_df['High'],
                low=main_df['Low'], close=main_df['Close'], name=ticker))
        
        if show_ma:
            fig.add_trace(go.Scatter(x=main_df.index, y=main_df['MA20'], line=dict(color='orange', width=1), name='MA20 (月線)'))
            fig.add_trace(go.Scatter(x=main_df.index, y=main_df['MA60'], line=dict(color='blue', width=1), name='MA60 (季線)'))

        if indicator == "布林通道 (Bollinger)":
            std = main_df['Close'].rolling(20).std()
            upper = main_df['MA20'] + (std * 2)
            lower = main_df['MA20'] - (std * 2)
            fig.add_trace(go.Scatter(x=main_df.index, y=upper, line=dict(color='rgba(200,200,200,0.5)', dash='dash'), name='Upper'))
            fig.add_trace(go.Scatter(x=main_df.index, y=lower, line=dict(color='rgba(200,200,200,0.5)', dash='dash'), name='Lower'))

        fig.update_layout(height=450, margin=dict(l=20, r=20, t=20, b=20), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # 2. 副圖 (MACD / RSI / Volume)
        if oscillator == "MACD (趨勢)":
            # 簡易 MACD 計算
            exp12 = main_df['Close'].ewm(span=12, adjust=False).mean()
            exp26 = main_df['Close'].ewm(span=26, adjust=False).mean()
            macd = exp12 - exp26
            signal = macd.ewm(span=9, adjust=False).mean()
            hist = macd - signal
            
            fig_osc = go.Figure()
            fig_osc.add_trace(go.Scatter(x=main_df.index, y=macd, name='MACD'))
            fig_osc.add_trace(go.Scatter(x=main_df.index, y=signal, name='Signal'))
            fig_osc.add_trace(go.Bar(x=main_df.index, y=hist, name='Histogram'))
            fig_osc.update_layout(height=200, margin=dict(t=0, b=0), title="MACD 指標")
            st.plotly_chart(fig_osc, use_container_width=True)

        elif oscillator == "RSI (強弱)":
            delta = main_df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            fig_osc = go.Figure(go.Scatter(x=main_df.index, y=rsi, name='RSI'))
            fig_osc.add_hline(y=70, line_dash="dash", line_color="red")
            fig_osc.add_hline(y=30, line_dash="dash", line_color="green")
            fig_osc.update_layout(height=200, margin=dict(t=0, b=0), title="RSI (14) 相對強弱指標")
            st.plotly_chart(fig_osc, use_container_width=True)

        # 3. 績效對決圖
        if compare_tickers:
            st.subheader("⚔️ 績效對決 (累積報酬率 %)")
            all_tickers = [ticker] + compare_tickers
            comp_df = get_normalized_data(all_tickers, timeframe)
            st.line_chart(comp_df)
            st.caption("註：起點設為 0%，高於 0 代表獲利，低於 0 代表虧損。")

    # === Tab 2: 風險與基本面 (Institutional Grade) ===
    with tab2:
        col_fund, col_risk = st.columns([1, 1])
        
        with col_fund:
            st.subheader("🏢 AI 基本面透視")
            try:
                info = yf.Ticker(ticker).info
                pe = info.get('trailingPE', 'N/A')
                pb = info.get('priceToBook', 'N/A')
                dy = info.get('dividendYield', 0)
                
                st.write(f"**公司**: {info.get('longName', ticker)}")
                st.write(f"**產業**: {info.get('industry', 'N/A')}")
                st.metric("本益比 (P/E)", pe)
                st.metric("股息殖利率", f"{dy*100:.2f}%" if dy else "N/A")
                
                if isinstance(pe, (int, float)):
                    if pe < 15: st.success("✅ 價值評估：相對便宜")
                    elif pe > 25: st.warning("⚠️ 價值評估：相對昂貴")
                    else: st.info("⚖️ 價值評估：價格合理")
            except:
                st.error("無法取得詳細基本面資料")

        with col_risk:
            st.subheader("🛡️ 量化風險壓力測試")
            # Max Drawdown 計算
            rolling_max = main_df['Close'].cummax()
            drawdown = (main_df['Close'] - rolling_max) / rolling_max
            mdd = drawdown.min()
            
            st.metric("歷史最大回撤 (MDD)", f"{mdd*100:.2f}%", help="過去這段期間最慘會賠多少")
            st.progress(int(100 + mdd*100)) # 視覺化條
            st.caption("資產防禦力 (MDD愈接近0愈好)")
            
            # 繪製回撤圖
            st.area_chart(drawdown * 100)
            st.caption("📉 歷史回撤路徑 (Drawdown History)")

    # === Tab 3: 財富模擬 (Interactive) ===
    with tab3:
        st.subheader("💰 複利引擎：預見你的未來")
        c_inv1, c_inv2, c_inv3 = st.columns(3)
        monthly_inv = c_inv1.number_input("每月定期定額", 1000, 100000, 5000)
        years = c_inv2.slider("持續投資年數", 1, 40, 10)
        rate = c_inv3.slider("預期年化報酬 (%)", 1, 20, 8)
        
        months = years * 12
        final_val = monthly_inv * (((1 + (rate/100)/12)**months - 1) / ((rate/100)/12))
        total_cost = monthly_inv * months
        profit = final_val - total_cost
        
        st.metric(f"{years} 年後預期資產", f"${final_val:,.0f}", f"淨利 +${profit:,.0f}")
        
        # 繪製成長曲線
        growth = [monthly_inv * (((1 + (rate/100)/12)**m - 1) / ((rate/100)/12)) for m in range(1, months+1)]
        st.area_chart(growth)

    # === Tab 4: 新聞情緒 (NLP) ===
    with tab4:
        st.subheader("📰 市場情緒掃描")
        
        def get_news_sentiment(symbol):
            url = f"https://www.google.com/search?q={symbol}+stock+news&tbm=nws"
            try:
                r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
                soup = BeautifulSoup(r.text, 'html.parser')
                titles = [h.text for h in soup.find_all('h3')[:8]]
                return titles
            except:
                return []

        news = get_news_sentiment(ticker)
        if news:
            score = 0
            # 簡單關鍵字權重
            pos_words = ['漲', '高', '強', '升', 'bull', 'high', 'jump', 'growth', 'gain']
            neg_words = ['跌', '低', '弱', '降', 'bear', 'low', 'drop', 'fall', 'cut']
            
            for t in news:
                st.write(f"• {t}")
                if any(w in t.lower() for w in pos_words): score += 1
                if any(w in t.lower() for w in neg_words): score -= 1
            
            st.markdown("---")
            st.write(f"**AI 情緒指數**: {score}")
            if score > 0: st.success("🔥 市場情緒：偏向樂觀")
            elif score < 0: st.error("🧊 市場情緒：偏向保守")
            else: st.warning("⚖️ 市場情緒：中立觀望")
        else:
            st.info("暫無即時新聞數據")

else:
    st.error("⚠️ 查無數據，請確認代碼是否正確 (台股需加 .TW，美股直接輸入代碼)")
