import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Stock Market Visualizer", layout="wide")
st.title("📊 我的 AI 股票視覺化工具")

ticker = st.sidebar.text_input("輸入股票代碼 (台股請加 .TW)", value="0050.TW")
timeframe = st.sidebar.selectbox("選擇時間範圍", ['1mo', '3mo', '6mo', '1y', '5y'], index=2)

# 下載數據，使用 group_by='column' 確保結構扁平化
data = yf.download(ticker, period=timeframe)

if not data.empty:
    # 解決 yfinance 多層索引問題
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    # 計算 20 日移動平均線 (MA)
    data['MA20'] = data['Close'].rolling(window=20).mean()
    
    # 建立圖表
    fig = go.Figure()

    # 1. 繪製 K 線圖
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='K線'
    ))
    
    # 2. 繪製 MA20 橘色線 (確保這段執行)
    fig.add_trace(go.Scatter(
        x=data.index, 
        y=data['MA20'], 
        line=dict(color='orange', width=2), 
        name='MA20 均線'
    ))
    
    # 圖表美化
    fig.update_layout(
        xaxis_rangeslider_visible=False, 
        height=600,
        title=f"{ticker} 走勢與 MA20 均線",
        yaxis_title="價格 (TWD)"
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # --- 找回並強化數據摘要區塊 ---
    st.markdown("---")
    st.subheader("📋 最近 5 個交易日數據摘要")
    
    # 整理要顯示的表格 (只取開、高、低、收與 MA20)
    display_df = data[['Open', 'High', 'Low', 'Close', 'MA20']].tail(5).copy()
    
    # 將日期格式化，只保留年月日
    display_df.index = display_df.index.strftime('%Y-%m-%d')
    
    # 使用 Streamlit 漂亮的 dataframe 組件顯示
    st.dataframe(display_df.style.format("{:.2f}").highlight_max(axis=0, color='#90ee90').highlight_min(axis=0, color='#ffcccb'))
    
    st.info("💡 提示：綠色背景代表該欄位近期最高，紅色代表最低。")
    
    # 檢查 MA20 是否有數值
    if data['MA20'].isnull().all():
        st.warning("⚠️ MA20 尚無數據（可能是數據量不足 20 筆），請選擇更長的時間範圍（如 6mo）。")
    else:
        st.success(f"成功繪製 {ticker} 及其均線！")
else:
    st.error("目前抓不到數據，請確認代碼。")

    # --- AI 投資試算模組 ---
st.markdown("---")
st.subheader("🔮 AI 投資回報試算器")

with st.expander("點擊展開：設定您的 (可調整) 年投資計畫", expanded=True):
    col_input1, col_input2, col_input3 = st.columns(3)
    
    with col_input1:
        monthly_invest = st.number_input("每月預計投入金額 (TWD)", value=1000, step=500)
    with col_input2:
        invest_years = st.slider("預計投資年數", 1, 30, 5)
    with col_input3:
        # 根據歷史數據，0050 年化報酬率約 8% - 10%
        expected_return = st.slider("預期年化報酬率 (%)", 1.0, 15.0, 8.0)

# 計算複利回報
# 複利公式：FV = P * [((1 + r/n)^(nt) - 1) / (r/n)]
monthly_rate = (expected_return / 100) / 12
months = invest_years * 12
final_value = monthly_invest * (((1 + monthly_rate)**months - 1) / monthly_rate)
total_cost = monthly_invest * months
total_profit = final_value - total_cost

# 顯示結果卡片
res_col1, res_col2, res_col3 = st.columns(3)
res_col1.metric("預估總資產", f"${final_value:,.0f}")
res_col2.metric("投入成本", f"${total_cost:,.0f}")
res_col3.metric("預估淨利", f"${total_profit:,.0f}", delta=f"{(total_profit/total_cost)*100:.1f}%")

# 繪製資產成長曲線
growth_data = []
for m in range(1, months + 1):
    val = monthly_invest * (((1 + monthly_rate)**m - 1) / monthly_rate)
    growth_data.append(val)

st.line_chart(growth_data)
st.caption(f"💡 AI 推測：若每年穩定回報 {expected_return}%，{invest_years} 年後您的資產將成長至 {final_value:,.0f} 元。")

import requests
from bs4 import BeautifulSoup

# --- AI 新聞情緒分析模組 ---
st.markdown("---")
st.subheader("📰 AI 市場情緒即時分析")

def fetch_google_news(stock_name):
    # 模擬抓取 Google News 標題 (以股票名稱搜尋)
    url = f"https://www.google.com/search?q={stock_name}+股市+新聞&tbm=nws"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    
    titles = []
    for g in soup.find_all('div', dict(reversed([('class', 'vv779c')])) )[:5]: # 抓取前 5 則
        if g.text:
            titles.append(g.text)
    
    # 如果抓不到特定標籤，改用通用抓取
    if not titles:
        for item in soup.find_all('h3')[:5]:
            titles.append(item.text)
    return titles

# 取得新聞
news_titles = fetch_google_news(ticker)

if news_titles:
    col_news, col_sentiment = st.columns([2, 1])
    
    with col_news:
        st.write(f"**關於 {ticker} 的最新標題：**")
        for t in news_titles:
            st.caption(f"• {t}")
            
    with col_sentiment:
        # 這裡模擬 AI 評分邏輯 (未來可串接 OpenAI API)
        sentiment_score = 0
        positive_words = ['漲', '紅', '利多', '優於預期', '買進', '成長', '噴發']
        negative_words = ['跌', '綠', '利空', '低於預期', '賣出', '衰退', '重挫']
        
        for t in news_titles:
            if any(w in t for w in positive_words): sentiment_score += 1
            if any(w in t for w in negative_words): sentiment_score -= 1
            
        st.write("**AI 情緒診斷：**")
        if sentiment_score > 0:
            st.success(f"🔥 偏向利多 (+{sentiment_score})")
            st.write("建議：市場氛圍樂觀，適合按計畫投入。")
        elif sentiment_score < 0:
            st.error(f"❄️ 偏向利空 ({sentiment_score})")
            st.write("建議：近期波動較大，可考慮分批入場。")
        else:
            st.warning("⚖️ 觀望中立 (0)")
            st.write("建議：目前無重大趨勢，維持定期定額。")
else:
    st.info("目前尚無即時新聞數據。")





#可能是新網頁
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup

# --- 頁面配置 ---
st.set_page_config(page_title="Pro Stock Visualizer", layout="wide")
st.title("📈 專業級 AI 投資指揮中心")

# --- 側邊欄設計 ---
st.sidebar.header("📊 參數控制面板")
ticker = st.sidebar.text_input("股票代碼", value="0050.TW")
timeframe = st.sidebar.selectbox("觀測週期", ['1mo', '3mo', '6mo', '1y', '5y'], index=2)

st.sidebar.markdown("---")
st.sidebar.subheader("🛠 技術指標設定")
show_ma = st.sidebar.checkbox("顯示 MA20 均線", value=True)
show_volume = st.sidebar.checkbox("顯示成交量圖", value=False)
indicator = st.sidebar.selectbox("進階疊加指標", ["無", "布林通道", "RSI (相對強弱)"])

# --- 核心數據抓取 ---
@st.cache_data
def get_stock_data(symbol, period):
    df = yf.download(symbol, period=period)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = get_stock_data(ticker, timeframe)

if not data.empty:
    # --- 分頁系統 ---
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 技術分析", "📋 歷史數據", "🔮 財富預測", "📰 AI 新聞"])

    # --- Tab 1: 技術分析 (圖表) ---
    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'],
                                     low=data['Low'], close=data['Close'], name='K線'))
        
        if show_ma:
            ma20 = data['Close'].rolling(window=20).mean()
            fig.add_trace(go.Scatter(x=data.index, y=ma20, line=dict(color='orange', width=1.5), name='MA20'))
            
        if indicator == "布林通道":
            ma20 = data['Close'].rolling(window=20).mean()
            std = data['Close'].rolling(window=20).std()
            fig.add_trace(go.Scatter(x=data.index, y=ma20 + (std * 2), line=dict(color='rgba(173, 216, 230, 0.5)', dash='dash'), name='布林上軌'))
            fig.add_trace(go.Scatter(x=data.index, y=ma20 - (std * 2), line=dict(color='rgba(173, 216, 230, 0.5)', dash='dash'), name='布林下軌'))
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=600, margin=dict(t=30, b=30))
        st.plotly_chart(fig, use_container_width=True)
        
        if show_volume:
            st.bar_chart(data['Volume'])

    # --- Tab 2: 歷史數據 ---
    with tab2:
        st.subheader("最近成交紀錄")
        st.dataframe(data.tail(10).style.format("{:.2f}"), use_container_width=True)

    # --- Tab 3: 財富預測 (複利計算) ---
    with tab3:
        st.subheader("每月 1,000 元定期定額試算")
        col_a, col_b = st.columns(2)
        with col_a:
            inv_amt = st.number_input("每月投入金額", value=1000)
            inv_years = st.slider("投資年數", 1, 30, 10)
        with col_b:
            ret_rate = st.slider("預期年化報酬率 (%)", 1, 15, 8)
            
        months = inv_years * 12
        rate = (ret_rate / 100) / 12
        final_val = inv_amt * (((1 + rate)**months - 1) / rate)
        st.metric("10 年後資產總額", f"${final_val:,.0f}", f"獲利 ${final_val - (inv_amt*months):,.0f}")

   # --- Tab 4: AI 新聞與情緒計分表 ---
    with tab4:
        st.subheader("📰 市場情緒即時看板")
        
        # 定義抓取函數 (若之前沒定義請放在程式碼上方)
        def fetch_google_news(stock_name):
            url = f"https://www.google.com/search?q={stock_name}+股市+新聞&tbm=nws"
            headers = {"User-Agent": "Mozilla/5.0"}
            try:
                response = requests.get(url, headers=headers, timeout=5)
                soup = BeautifulSoup(response.text, "html.parser")
                titles = [item.text for item in soup.find_all('h3')[:6]]
                return titles
            except:
                return []

        news_titles = fetch_google_news(ticker)

        if news_titles:
            # 1. 情緒計分邏輯
            pos_words = ['漲', '紅', '利多', '優於預期', '買進', '成長', '噴發', '強勢']
            neg_words = ['跌', '綠', '利空', '低於預期', '賣出', '衰退', '重挫', '保守']
            
            score = 0
            for t in news_titles:
                for w in pos_words:
                    if w in t: score += 1
                for w in neg_words:
                    if w in t: score -= 1
            
            # 2. 顯示情緒儀表 (計分表)
            col_score, col_list = st.columns([1, 2])
            
            with col_score:
                st.markdown("### AI 診斷結果")
                # 根據分數顯示顏色
                if score > 0:
                    st.metric("情緒總分", f"+{score}", "🔥 樂觀", delta_color="normal")
                    st.success("市場氛圍偏向利多，投資情緒高昂。")
                elif score < 0:
                    st.metric("情緒總分", f"{score}", "❄️ 悲觀", delta_color="inverse")
                    st.error("市場氛圍偏向利空，建議謹慎操作。")
                else:
                    st.metric("情緒總分", "0", "⚖️ 中立")
                    st.warning("目前訊息紛雜，市場正在尋找方向。")
                
                st.progress(min(max((score + 5) * 10, 0), 100)) # 簡易進度條顯示強弱
                st.caption("情緒量尺 (-5 到 +5)")

            with col_list:
                st.markdown("### 最新新聞標題")
                for i, t in enumerate(news_titles):
                    st.write(f"{i+1}. {t}")
                    st.divider()
        else:
            st.info("暫時無法獲取即時新聞，請稍後再試。")

