import streamlit as st
from components import Chart

st.set_page_config(
    page_title="Customer Cohort Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(f"""
<style>
    /* Main theme colors */
    :root {{
        --primary-color: {"#0D9488"};
    }}
    
    /* KPI Card Styling */
    .kpi-card {{
        background: linear-gradient(135deg, var(--primary-color) 0%, #0ea5a5 100%);
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        color: white;
        text-align: center;
    }}
    
    .kpi-value {{
        font-size: 2.75rem;
        font-weight: bold;
        margin: 10px 0;
    }}
    
    .kpi-label {{
        font-size: 1rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    
    .kpi-delta {{
        font-size: 12px;
        margin-top: 5px;
    }}
    
    /* Header styling */
    .main-header {{
        text-align: center;
        padding: 20px 0;
        background: linear-gradient(90deg, var(--primary-color) 0%, #0ea5a5 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 30px;
    }}
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        margin-top: 32px;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        padding: 10px 20px;
        background-color: transparent;
        border-radius: 5px;
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: var(--primary-color);
        color: white;
    }}

    .st-ce{{
        background-color: #0D9488;
    }}
</style>
""", unsafe_allow_html=True)


st.title('📊 Customer Cohort Analysis Dashboard')
st.caption(
    'Comprehensive insights into customer behavior, revenue trends, and operational performance')

c = Chart('data/cohort.csv')
with st.sidebar:
    st.header("🔍 Filters")

    st.subheader("Date Range")
    min_date = c.df['order_date'].min()
    max_date = c.df['order_date'].max()

    date_range = st.date_input(
        "Select date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key='date_range'
    )

    st.subheader("Region")
    all_regions = c.unique_values('Region')
    region = st.multiselect(
        "Select regions",
        options=all_regions,
        default=all_regions,
    )

    st.subheader("Category")
    all_categories = c.unique_values('category')
    category = st.multiselect(
        "Select categories",
        options=all_categories,
        default=all_categories,
    )

    st.subheader("Order Status")
    all_statuses = c.unique_values('status')
    status = st.multiselect(
        "Select order statuses",
        options=all_statuses,
        default=all_statuses
    )

c.set_filters(
    date_range=date_range,
    Region=region,
    category=category,
    status=status
)

kpis = c.compute_kpis()
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">💰 Total Revenue</div>
        <div class="kpi-value">${kpis['total_revenue']:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">👥 Total Customers</div>
        <div class="kpi-value">{kpis['total_customers']:,}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">📦 Total Orders</div>
        <div class="kpi-value">{kpis['total_orders']:,}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">💳 Average Order Value</div>
        <div class="kpi-value">${kpis['aov']:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Row 2
col5, col6, col7, col8 = st.columns(4)

with col5:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">⭐ Customer Lifetime Value</div>
        <div class="kpi-value">${kpis['clv']:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

with col6:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">🔄 Repeat Purchase Rate</div>
        <div class="kpi-value">{kpis['repeat_rate']:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col7:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">📊 Avg Items per Order</div>
        <div class="kpi-value">{kpis['items_per_order']:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

with col8:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">✅ Order Completion Rate</div>
        <div class="kpi-value">{kpis['completion_rate']:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Cohort Analysis",
    "💰 Revenue Analysis",
    "👥 Customer Behavior",
    "🌍 Regional & Demographics",
    "📦 Order Status & Operations",
])

with tab1:
    st.markdown("### 📊 Cohort Analysis")

    col1, col2 = st.columns(2)
    with col1:

        st.plotly_chart(c.plot_cohort_retention_heatmap(), width='stretch')
    with col2:
        st.plotly_chart(c.plot_cohort_size_distribution(), width='stretch')

    st.plotly_chart(c.plot_average_retention_curve(), width='stretch')

with tab2:
    st.markdown("### 💰 Revenue Analysis")

    st.plotly_chart(c.plot_revenue_trend(), width='stretch')

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(c.plot_revenue_by_category(), width='stretch')
    with col2:
        st.plotly_chart(c.plot_revenue_by_payment(), width='stretch')

    st.plotly_chart(c.plot_top_products(), width='stretch')


with tab3:
    st.markdown("### 👥 Customer Behavior")

    st.plotly_chart(c.plot_rfm_segmentation(), width='stretch')

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(c.plot_purchase_frequency(), width='stretch')
    with col2:
        st.plotly_chart(c.plot_clv_distribution(), width='stretch')

    st.plotly_chart(c.plot_time_between_purchases(), width='stretch')

with tab4:
    st.markdown("### 🌍 Regional & Demographics")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(c.plot_revenue_by_region(), width='stretch')
    with col2:
        st.plotly_chart(c.plot_age_distribution(), width='stretch')

    st.plotly_chart(c.plot_regional_performance_matrix(), width='stretch')

    st.plotly_chart(c.plot_category_by_region(), width='stretch')

with tab5:
    st.markdown("### 📦 Order Status & Operations")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(c.plot_order_status_funnel(), width='stretch')

    with col2:
        st.plotly_chart(c.plot_order_status_trend(), width='stretch')

    st.plotly_chart(c.plot_cancellation_analysis(), width='stretch')
    st.plotly_chart(c.plot_order_heatmap(), width='stretch')
