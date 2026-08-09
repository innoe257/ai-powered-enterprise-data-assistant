"""Financial Dashboard Component."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render_financial_dashboard():
    """Render the financial dashboard with charts and metrics."""
    
    ticker = st.session_state.selected_ticker
    xbrl_data = st.session_state.xbrl_data
    
    st.markdown(f"### 📈 {ticker} Financial Overview")
    
    if ticker not in xbrl_data or xbrl_data[ticker] is None:
        st.warning(f"No financial data available for {ticker}")
        return
    
    # Load data
    metrics = xbrl_data[ticker]
    
    # Key metrics cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        revenue = get_latest_value(metrics, 'revenue')
        st.metric("Revenue (TTM)", format_currency(revenue))
    
    with col2:
        net_income = get_latest_value(metrics, 'netincome')
        st.metric("Net Income", format_currency(net_income))
    
    with col3:
        total_assets = get_latest_value(metrics, 'totalassets')
        st.metric("Total Assets", format_currency(total_assets))
    
    with col4:
        fcf = get_latest_value(metrics, 'freecashflow')
        st.metric("Free Cash Flow", format_currency(fcf))
    
    st.markdown("---")
    
    # Revenue trend chart
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("#### Revenue Trend")
        revenue_df = get_metric_df(metrics, 'revenue')
        if revenue_df is not None:
            fig = px.bar(
                revenue_df,
                x='period',
                y='value',
                color='fiscal_period',
                title=f'{ticker} Revenue by Period',
                labels={'value': 'Revenue (USD)', 'period': 'Period'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Revenue data not available")
    
    with col_right:
        st.markdown("#### Profitability Metrics")
        profit_df = build_profitability_df(metrics)
        if profit_df is not None:
            fig = go.Figure()
            for metric in ['Revenue', 'Net Income', 'Operating Income']:
                if metric in profit_df.columns:
                    fig.add_trace(go.Scatter(
                        x=profit_df['period'],
                        y=profit_df[metric],
                        mode='lines+markers',
                        name=metric
                    ))
            fig.update_layout(
                title=f'{ticker} Profitability Trends',
                xaxis_title='Period',
                yaxis_title='Amount (USD)',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Profitability data not available")
    
    # Financial statements table
    st.markdown("---")
    st.markdown("#### 📋 Latest Financial Data")
    
    tabs = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])
    
    with tabs[0]:
        display_metric_table(metrics, ['revenue', 'netincome', 'operatingincome'])
    
    with tabs[1]:
        display_metric_table(metrics, ['totalassets', 'totalliabilities', 'stockholdersequity'])
    
    with tabs[2]:
        display_metric_table(metrics, ['operatingcashflow', 'freecashflow', 'capitalexpenditures'])


def get_latest_value(metrics: dict, metric_name: str):
    """Get the latest value for a metric."""
    if metric_name not in metrics or metrics[metric_name] is None:
        return None
    df = metrics[metric_name]
    if df.empty:
        return None
    latest = df.sort_values('period_end', ascending=False).iloc[0]
    return latest['numeric_value']


def get_metric_df(metrics: dict, metric_name: str):
    """Get a metric as a DataFrame for plotting."""
    if metric_name not in metrics or metrics[metric_name] is None:
        return None
    df = metrics[metric_name].copy()
    if df.empty:
        return None
    df['period'] = df['fiscal_year'].astype(str) + ' ' + df['fiscal_period']
    df['value'] = df['numeric_value']
    return df


def build_profitability_df(metrics: dict):
    """Build a combined profitability DataFrame."""
    dfs = []
    metric_names = {
        'revenue': 'Revenue',
        'netincome': 'Net Income',
        'operatingincome': 'Operating Income'
    }
    
    for key, label in metric_names.items():
        if key in metrics and metrics[key] is not None:
            df = metrics[key].copy()
            if not df.empty:
                df['metric'] = label
                df['value'] = df['numeric_value']
                dfs.append(df[['period_end', 'fiscal_year', 'fiscal_period', 'metric', 'value']])
    
    if not dfs:
        return None
    
    combined = pd.concat(dfs, ignore_index=True)
    pivot = combined.pivot_table(
        index=['period_end', 'fiscal_year', 'fiscal_period'],
        columns='metric',
        values='value'
    ).reset_index()
    pivot['period'] = pivot['fiscal_year'].astype(str) + ' ' + pivot['fiscal_period']
    return pivot


def display_metric_table(metrics: dict, metric_keys: list):
    """Display a table of metrics."""
    rows = []
    for key in metric_keys:
        if key in metrics and metrics[key] is not None:
            df = metrics[key]
            if not df.empty:
                latest = df.sort_values('period_end', ascending=False).iloc[0]
                rows.append({
                    'Metric': key.replace('_', ' ').title(),
                    'Value': format_currency(latest['numeric_value']),
                    'Period': f"{latest['fiscal_year']} {latest['fiscal_period']}",
                    'YoY Change': 'N/A'  # Would need prior period comparison
                })
    
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.info("Data not available")


def format_currency(value):
    """Format a numeric value as currency."""
    if value is None:
        return "N/A"
    if abs(value) >= 1e12:
        return f"${value/1e12:.2f}T"
    elif abs(value) >= 1e9:
        return f"${value/1e9:.2f}B"
    elif abs(value) >= 1e6:
        return f"${value/1e6:.2f}M"
    else:
        return f"${value:,.0f}"
