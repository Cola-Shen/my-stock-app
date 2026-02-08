import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup

# --- 1. 頁面基本配置 ---
st.set_page_config(page_title="Pro AI Stock Station", layout="wide")
st.title("📈 專業級 AI 投資指揮中心")

# --- 2. 側邊欄設計 ---
st.sidebar.header("📊 參數控制面板")
ticker = st.sidebar.text_input("主標的代碼 (台股請加 .TW)", value="0050.TW")
timeframe = st.sidebar.selectbox("觀測週期", ['1mo', '3mo', '6mo', '1y', '5y', 'max'], index=2)

st.sidebar.markdown("---")
st.sidebar.subheader("⚖️ 績效比較 (對照組)")
# 讓用戶可以選擇多支股票進行報酬率 PK
compare_tickers = st.sidebar.multiselect(
    "選擇要比較的標的 (多選)",
    options=["2330.TW", "2454.TW", "2317.TW", "0056.TW", "AAPL", "TSLA", "VOO"],
    default=[]
)

st.sidebar.markdown("---")
st.sidebar.subheader("🛠 技術指標設定")
show_ma = st.sidebar.checkbox("顯示 MA20 均線", value=True)
show_volume = st.sidebar.checkbox("顯示成交量圖", value=True)
indicator = st.sidebar.selectbox("進階疊加指標", ["無", "布林通道", "RSI (相對強弱)"])

# --- 3. 核心數據抓取與處理函數 ---
@st.cache_data(ttl=3600)
def get_stock_data(symbol, period):
    df = yf.download(symbol, period=period)
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # 計算 20 日移動平均線 (MA)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    return df

def get_normalized_data(tickers, period):
    """計算所有標的的百分比報酬率，將起點設為 100"""
    combined = pd.DataFrame()
    for t in tickers:
        df = yf.download(t, period=period)['Close']
        if df.empty: continue
        if isinstance(df, pd.DataFrame): df = df.iloc[:, 0]
        # 標準化公式：(今日價格 / 第一日價格) * 100
        combined[t] = (df / df.iloc[0]) * 100
    return combined

# 執行主標的數據抓取
data = get_stock_data(ticker, timeframe)

# --- 4. 網頁主體內容 ---
if not data.empty:
    # 頂部即時數據摘要卡片
    curr_p = float(data['Close'].iloc[-1])
    prev_p = float(data['Close'].iloc[-2])
    change = curr_p - prev_p
    
    col_i1, col_i2, col_i3, col_i4 = st.columns(4)
    col_i1.metric(f"{ticker} 當前股價", f"${curr_p:,.2f}", f"{change:+.2f}")
    col_i2.metric("20日均線 (MA20)", f"${data['MA20'].iloc[-1]:,.2f}")
    col_i3.metric("今日成交量", f"{data['Volume'].iloc[-1]:,.0f}")
    
    # 智能警示邏輯
    if curr_p < data['MA20'].iloc[-1]:
        col_i4.warning("💡 建議：股價低於均線")
    else:
        col_i4.success("✨ 趨勢：股價高於均線")

    # --- 分頁系統 ---
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 技術分析與 PK", "📋 歷史數據", "🔮 財富預測", "📰 AI 新聞情緒"])

    # --- Tab 1: 技術分析與多股 PK ---
    with tab1:
        # 主 K 線圖
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'],
                                     low=data['Low'], close=data['Close'], name=f'{ticker} K線'))
        if show_ma:
            fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], line=dict(color='orange', width=1.5), name='MA20'))
        
        # 布林通道邏輯
        if indicator == "布林通道":
            std = data['Close'].rolling(window=20).std()
            upper = data['MA20'] + (std * 2)
            lower = data['MA20'] - (std * 2)
            fig.add_trace(go.Scatter(x=data.index, y=upper, line=dict(color='rgba(173, 216, 230, 0.4)', dash='dash'), name='布林上軌'))
            fig.add_trace(go.Scatter(x=data.index, y=lower, line=dict(color='rgba(173, 216, 230, 0.4)', dash='dash'), name='布林下軌'))
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=500, title=f"{ticker} 走勢圖")
        st.plotly_chart(fig, use_container_width=True)

        # 多股報酬率 PK 圖 (當用戶有選擇對照組時顯示)
        if compare_tickers:
            st.markdown("---")
            st.subheader("⚖️ 績效百分比對照 (以起始點為 100%)")
            all_list = [ticker] + compare_tickers
            comp_df = get_normalized_data(all_list, timeframe)
            
            fig_comp = go.Figure()
            for t in comp_df.columns:
                fig_comp.add_trace(go.Scatter(x=comp_df.index, y=comp_df[t], name=t, mode='lines'))
            
            fig_comp.update_layout(height=400, yaxis_title="報酬率基數 (100 為起點)", hovermode="x unified")
            st.plotly_chart(fig_comp, use_container_width=True)
            st.caption("💡 說明：此圖顯示若在觀測起點各投入相同金額，各標的的資產增長倍數。")

        if show_volume:
            st.bar_chart(data['Volume'])

    # --- Tab 2: 歷史數據與基本面 ---
    with tab2:
        st.subheader("📋 最近 10 個交易日數據")
        display_df = data[['Open', 'High', 'Low', 'Close', 'MA20']].tail(10).copy()
        display_df.index = display_df.index.strftime('%Y-%m-%d')
        st.dataframe(display_df.style.format("{:.2f}").highlight_max(axis=0, color='#90ee90'), use_container_width=True)
        
        st.markdown("---")
        st.subheader("🏢 公司基本面摘要")
        try:
            info = yf.Ticker(ticker).info
            c1, c2, c3 = st.columns(3)
            with c1:
                st.write(f"**公司名稱:** {info.get('longName', 'N/A')}")
                st.write(f"**產業:** {info.get('industry', 'N/A')}")
            with c2:
                st.write(f"**本益比 (P/E):** {info.get('trailingPE', 'N/A')}")
                st.write(f"**股息殖利率:** {info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "股息殖利率: N/A")
            with c3:
                st.write(f"**市值:** ${info.get('marketCap', 0):,.0f}")
                st.write(f"**52週高點:** {info.get('fiftyTwoWeekHigh', 'N/A')}")
        except:
            st.info("無法抓取詳細基本面數據，可能該代碼不支援 info 接口。")

    # --- Tab 3: 財富預測 ---
    with tab3:
        st.subheader("🔮 定期定額複利成長試算")
        col_a, col_b = st.columns(2)
        with col_a:
            inv_amt = st.number_input("每月預計投入金額 (TWD)", value=1000, step=500)
            inv_years = st.slider("預計投資年數", 1, 30, 10)
        with col_b:
            ret_rate = st.slider("預期年化報酬率 (%)", 1.0, 15.0, 8.0)
            
        months = inv_years * 12
        m_rate = (ret_rate / 100) / 12
        f_val = inv_amt * (((1 + m_rate)**months - 1) / m_rate)
        
        st.metric(f"{inv_years} 年後資產總額", f"${f_val:,.0f}", f"獲利 ${f_val - (inv_amt*months):,.0f}")
        
        growth = [inv_amt * (((1 + m_rate)**m - 1) / m_rate) for m in range(1, months + 1)]
        st.area_chart(growth)

    # --- Tab 4: AI 新聞情緒 ---
    with tab4:
        st.subheader("📰 市場情緒即時診斷")
        def fetch_news(name):
            url = f"https://www.google.com/search?q={name}+股市+新聞&tbm=nws"
            try:
                res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                soup = BeautifulSoup(res.text, "html.parser")
                return [item.text for item in soup.find_all('h3')[:6]]
            except: return []

        titles = fetch_news(ticker)
        if titles:
            score = 0
            pos = ['漲', '紅', '利多', '優於預期', '買進', '成長', '噴發']
            neg = ['跌', '綠', '利空', '低於預期', '賣出', '衰退', '重挫']
            for t in titles:
                for w in pos: 
                    if w in t: score += 1
                for w in neg: 
                    if w in t: score -= 1
            
            cs1, cs2 = st.columns([1, 2])
            with cs1:
                st.metric("情緒總分", score, "樂觀🔥" if score > 0 else "保守❄️")
                st.progress(min(max((score + 5) * 10, 0), 100))
                st.caption("AI 建議：保持定期定額，分批佈局。")
            with cs2:
                for i, t in enumerate(titles):
                    st.write(f"{i+1}. {t}")
                    st.divider()
        else:
            st.info("暫無新聞數據，請稍後再試。")
else:
    st.error("查無數據，請檢查股票代碼是否正確。")
