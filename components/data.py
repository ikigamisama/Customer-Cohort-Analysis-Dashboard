import pandas as pd
import streamlit as st
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


PRIMARY_COLOR = "#2596be"
CHURNED_COLOR = "#FF6B6B"
STAYED_COLOR = "#51CF66"
JOINED_COLOR = "#4DABF7"


@st.cache_data
def load_data(csv_file: str) -> pd.DataFrame:
    df = pd.read_csv(csv_file, low_memory=False)
    return df


class Data:
    def __init__(self, csv_file):
        self.df = load_data(csv_file)
        self.filtered_df = self.df.copy()
        self.init_feat_df()

        self.filters = {
            "date_range": None,
            'Region': None,
            'category': None,
            'status': None
        }

    def init_feat_df(self):
        self.df['order_date'] = pd.to_datetime(
            self.df['order_date'], format='%d-%m-%Y')
        self.df['customer_since'] = pd.to_datetime(
            self.df['Customer Since'], format='%m/%d/%Y', errors='coerce')

        self.df['revenue'] = (self.df['qty_ordered'] *
                              self.df['price']) - self.df['discount_amount']

        self.df['order_month'] = self.df['order_date'].dt.to_period('M')
        self.df['cohort_month'] = self.df['customer_since'].dt.to_period('M')
        self.df['order_year'] = self.df['order_date'].dt.year
        self.df['order_month_name'] = self.df['order_date'].dt.strftime(
            '%B %Y')
        self.df['day_of_week'] = self.df['order_date'].dt.day_name()
        self.df['hour'] = self.df['order_date'].dt.hour

    def set_filters(self, **kwargs):
        self.filters.update(kwargs)
        self.apply_filters()

    def apply_filters(self):
        df = self.df.copy()

        date_range = self.filters.get("date_range")
        if date_range and len(date_range) == 2:
            start_date = pd.to_datetime(date_range[0])
            end_date = pd.to_datetime(date_range[1])
            df = df[
                (df['order_date'] >= start_date) &
                (df['order_date'] <= end_date)
            ]

        for column in ["Region", "category", "status"]:
            values = self.filters.get(column)
            if values and len(values) > 0:
                df = df[df[column].isin(values)]

        self.filtered_df = df

    def unique_values(self, column):
        return sorted(self.df[column].dropna().unique())

    def compute_kpis(self):
        df = self.filtered_df
        total_revenue = df['revenue'].sum()
        total_customers = df['cust_id'].nunique()
        total_orders = df['order_id'].nunique()
        total_items = df['qty_ordered'].sum()

        aov = total_revenue / total_orders if total_orders > 0 else 0
        clv = total_revenue / total_customers if total_customers > 0 else 0

        # Repeat purchase rate
        customer_orders = df.groupby('cust_id')['order_id'].nunique()
        repeat_customers = (customer_orders > 1).sum()
        repeat_rate = (repeat_customers / total_customers *
                       100) if total_customers > 0 else 0

        # Items per order
        items_per_order = total_items / total_orders if total_orders > 0 else 0

        # Completion rate
        completed_orders = df[df['status'] == 'complete']['order_id'].nunique()
        completion_rate = (completed_orders / total_orders *
                           100) if total_orders > 0 else 0

        return {
            'total_revenue': total_revenue,
            'total_customers': total_customers,
            'total_orders': total_orders,
            'aov': aov,
            'clv': clv,
            'repeat_rate': repeat_rate,
            'repeat_customers': repeat_customers,
            'items_per_order': items_per_order,
            'completion_rate': completion_rate,
            'completed_orders': completed_orders
        }


def get_title_style():
    theme = st.get_option("theme.base") or "light"

    return {
        'font': {
            'size': 22,
            'color': 'white' if theme != "dark" else "#2d3748"
        }
    }


class Chart(Data):
    def __init__(self, csv_file: str, theme: str = "plotly"):
        super().__init__(csv_file)
        self.theme = theme

    def calculate_cohort_data(self):
        df_cohort = self.filtered_df.groupby(['cohort_month', 'order_month']).agg({
            'cust_id': 'nunique'
        }).reset_index()

        # Calculate cohort age
        df_cohort['cohort_age'] = (
            df_cohort['order_month'].astype(str).str[:7].apply(lambda x: pd.Period(x, freq='M')) -
            df_cohort['cohort_month']
        ).apply(lambda x: x.n)

        # Get cohort sizes
        cohort_sizes = self.filtered_df.groupby(
            'cohort_month')['cust_id'].nunique()

        # Calculate retention rate
        df_cohort = df_cohort.merge(
            cohort_sizes.rename('cohort_size'),
            left_on='cohort_month',
            right_index=True
        )
        df_cohort['retention_rate'] = (
            df_cohort['cust_id'] / df_cohort['cohort_size']) * 100

        return df_cohort

    def calculate_rfm(self):
        current_date = self.filtered_df['order_date'].max()

        rfm = self.filtered_df.groupby('cust_id').agg({
            'order_date': lambda x: (current_date - x.max()).days,  # Recency
            'order_id': 'nunique',  # Frequency
            'revenue': 'sum'  # Monetary
        }).reset_index()

        rfm.columns = ['cust_id', 'recency', 'frequency', 'monetary']

        # Segment customers
        rfm['segment'] = 'Low Value'
        rfm.loc[(rfm['frequency'] >= 3) & (rfm['monetary'] >=
                                           rfm['monetary'].median()), 'segment'] = 'High Value'
        rfm.loc[(rfm['recency'] > 90) & (
            rfm['frequency'] >= 2), 'segment'] = 'At Risk'
        rfm.loc[rfm['frequency'] == 1, 'segment'] = 'New'

        return rfm

    def plot_cohort_retention_heatmap(self):
        df_cohort = self.calculate_cohort_data()

        # Pivot for heatmap
        cohort_pivot = df_cohort.pivot_table(
            index='cohort_month',
            columns='cohort_age',
            values='retention_rate'
        )

        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=cohort_pivot.values,
            x=cohort_pivot.columns,
            y=[str(idx) for idx in cohort_pivot.index],
            colorscale='Teal',
            text=np.round(cohort_pivot.values, 1),
            texttemplate='%{text}%',
            textfont={"size": 10},
            colorbar=dict(title="Retention %")
        ))

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Customer Retention by Cohort Month",
                **title_style
            },
            xaxis_title="Cohort Age (Months)",
            yaxis_title="Cohort Month",
            height=500
        )

        return fig

    def plot_cohort_size_distribution(self):
        cohort_sizes = self.filtered_df.groupby('cohort_month')[
            'cust_id'].nunique().reset_index()
        cohort_sizes.columns = ['cohort_month', 'customers']
        cohort_sizes['cohort_month'] = cohort_sizes['cohort_month'].astype(str)

        fig = px.bar(
            cohort_sizes.sort_values('customers', ascending=True),
            x='customers',
            y='cohort_month',
            orientation='h',
            color='customers',
            color_continuous_scale='Teal',
            text='customers'
        )

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Acquisition Cohort Sizes",
                **title_style
            },
            xaxis_title="Number of Customers",
            yaxis_title="Cohort Month",
            height=500,
            showlegend=False
        )
        fig.update_traces(textposition='outside')

        return fig

    def plot_average_retention_curve(self):
        df_cohort = self.calculate_cohort_data()

        avg_retention = df_cohort.groupby('cohort_age')['retention_rate'].agg([
            'mean', 'std']).reset_index()

        fig = go.Figure()

        # Main line
        fig.add_trace(go.Scatter(
            x=avg_retention['cohort_age'],
            y=avg_retention['mean'],
            mode='lines+markers',
            name='Average Retention',
            line=dict(color=PRIMARY_COLOR, width=3),
            marker=dict(size=8)
        ))

        # Confidence interval
        fig.add_trace(go.Scatter(
            x=avg_retention['cohort_age'],
            y=avg_retention['mean'] + avg_retention['std'],
            mode='lines',
            name='Upper Bound',
            line=dict(width=0),
            showlegend=False
        ))

        fig.add_trace(go.Scatter(
            x=avg_retention['cohort_age'],
            y=avg_retention['mean'] - avg_retention['std'],
            mode='lines',
            name='Lower Bound',
            line=dict(width=0),
            fillcolor='rgba(13, 148, 136, 0.2)',
            fill='tonexty',
            showlegend=False
        ))

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Average Retention Rate Over Time",
                **title_style
            },
            xaxis_title="Cohort Age (Months)",
            yaxis_title="Retention Rate (%)",
            height=400,
            hovermode='x unified'
        )

        return fig

    def plot_revenue_trend(self):
        monthly_revenue = self.filtered_df.groupby('order_month_name').agg({
            'revenue': 'sum',
            'order_date': 'first'
        }).reset_index()

        monthly_revenue = monthly_revenue.sort_values('order_date')
        monthly_revenue['cumulative_revenue'] = monthly_revenue['revenue'].cumsum()

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=monthly_revenue['order_month_name'],
            y=monthly_revenue['revenue'],
            name='Monthly Revenue',
            fill='tozeroy',
            line=dict(color=PRIMARY_COLOR, width=2)
        ))

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Monthly Revenue Trend",
                **title_style
            },
            xaxis_title="Month",
            yaxis_title="Revenue ($)",
            height=400,
            hovermode='x unified'
        )

        return fig

    def plot_revenue_by_category(self):
        category_revenue = self.filtered_df.groupby(
            'category')['revenue'].sum().reset_index()
        category_revenue = category_revenue.sort_values(
            'revenue', ascending=False)

        fig = px.treemap(
            category_revenue,
            path=['category'],
            values='revenue',
            color='revenue',
            color_continuous_scale='Teal',
            title="Revenue Distribution by Category"
        )

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Revenue Distribution by Category",
                **title_style
            },
            height=450
        )

        return fig

    def plot_top_products(self):
        product_revenue = self.filtered_df.groupby(['sku', 'category']).agg({
            'revenue': 'sum',
            'qty_ordered': 'sum'
        }).reset_index()
        product_revenue = product_revenue.sort_values(
            'revenue', ascending=False).head(10)

        fig = px.bar(
            product_revenue.sort_values('revenue', ascending=True),
            x='revenue',
            y='sku',
            orientation='h',
            color='category',
            text='revenue',
            color_discrete_sequence=px.colors.sequential.Teal
        )

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Top 10 Products by Revenue",
                **title_style
            },
            xaxis_title="Revenue ($)",
            yaxis_title="Product SKU",
            height=500
        )
        fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')

        return fig

    def plot_revenue_by_payment(self):
        payment_revenue = self.filtered_df.groupby('payment_method')[
            'revenue'].sum().reset_index()
        payment_revenue = payment_revenue.sort_values(
            'revenue', ascending=False)

        fig = px.pie(
            payment_revenue,
            values='revenue',
            names='payment_method',
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Teal
        )

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Revenue Distribution by Payment Method",
                **title_style
            },
            height=400
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')

        return fig

    def plot_rfm_segmentation(self):
        rfm = self.calculate_rfm()

        fig = px.scatter(
            rfm,
            x='recency',
            y='frequency',
            size='monetary',
            color='segment',
            hover_data=['cust_id'],
            color_discrete_map={
                'High Value': PRIMARY_COLOR,
                'At Risk': '#FF6B35',
                'New': '#0068C9',
                'Low Value': '#8B5CF6'
            }
        )

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "RFM Customer Segmentation",
                **title_style
            },
            xaxis_title="Recency (Days Since Last Purchase)",
            yaxis_title="Frequency (Number of Orders)",
            height=500
        )

        return fig

    def plot_purchase_frequency(self):
        customer_orders = self.filtered_df.groupby(
            'cust_id')['order_id'].nunique().reset_index()
        customer_orders.columns = ['cust_id', 'order_count']

        fig = px.histogram(
            customer_orders,
            x='order_count',
            nbins=20,
            color_discrete_sequence=[PRIMARY_COLOR]
        )

        # Add mean line
        mean_orders = customer_orders['order_count'].mean()
        fig.add_vline(x=mean_orders, line_dash="dash", line_color="red",
                      annotation_text=f"Mean: {mean_orders:.1f}")

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Distribution of Purchase Frequency",
                **title_style
            },
            xaxis_title="Number of Orders per Customer",
            yaxis_title="Number of Customers",
            height=400
        )

        return fig

    def plot_clv_distribution(self):
        customer_clv = self.filtered_df.groupby(
            'cust_id')['revenue'].sum().reset_index()
        customer_clv.columns = ['cust_id', 'clv']

        # Add segment
        rfm = self.calculate_rfm()
        customer_clv = customer_clv.merge(
            rfm[['cust_id', 'segment']], on='cust_id')

        fig = px.box(
            customer_clv,
            x='segment',
            y='clv',
            color='segment',
            color_discrete_map={
                'High Value': PRIMARY_COLOR,
                'At Risk': '#FF6B35',
                'New': '#0068C9',
                'Low Value': '#8B5CF6'
            }
        )

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Customer Lifetime Value Distribution by Segment",
                **title_style
            },
            xaxis_title="Customer Segment",
            yaxis_title="CLV ($)",
            height=450,
            showlegend=False
        )

        return fig

    def plot_time_between_purchases(self):
        customer_dates = self.filtered_df.groupby(
            'cust_id')['order_date'].apply(list).reset_index()
        customer_dates = customer_dates[customer_dates['order_date'].apply(
            len) > 1]

        time_diffs = []
        for dates in customer_dates['order_date']:
            sorted_dates = sorted(dates)
            diffs = [(sorted_dates[i+1] - sorted_dates[i]).days
                     for i in range(len(sorted_dates)-1)]
            time_diffs.extend(diffs)

        if time_diffs:
            fig = px.histogram(
                x=time_diffs,
                nbins=30,
                color_discrete_sequence=[PRIMARY_COLOR]
            )

            median_days = np.median(time_diffs)
            mean_days = np.mean(time_diffs)

            fig.add_vline(x=median_days, line_dash="dash", line_color="blue",
                          annotation_text=f"Median: {median_days:.0f} days")
            fig.add_vline(x=mean_days, line_dash="dash", line_color="red",
                          annotation_text=f"Mean: {mean_days:.0f} days")

            title_style = get_title_style()
            fig.update_layout(
                title={
                    'text': "Average Time Between Purchases",
                    **title_style
                },
                xaxis_title="Days Between Consecutive Purchases",
                yaxis_title="Frequency",
                height=400
            )
        else:
            fig = go.Figure()
            title_style = get_title_style()
            fig.update_layout(
                title={
                    'text': "No repeat purchase data available",
                    **title_style
                }
            )

        return fig

    def plot_revenue_by_region(self):
        regional_revenue = self.filtered_df.groupby(
            'Region')['revenue'].sum().reset_index()
        regional_revenue = regional_revenue.sort_values(
            'revenue', ascending=False)

        fig = px.bar(
            regional_revenue,
            x='Region',
            y='revenue',
            color='revenue',
            color_continuous_scale='Teal',
            text='revenue'
        )

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Regional Revenue Distribution",
                **title_style
            },
            xaxis_title="Region",
            yaxis_title="Revenue ($)",
            height=400,
            showlegend=False
        )
        fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')

        return fig

    def plot_age_distribution(self):
        # Get unique customers with their age
        customer_age = self.filtered_df.groupby('cust_id').agg({
            'age': 'first',
            'Gender': 'first'
        }).reset_index()

        fig = px.histogram(
            customer_age,
            x='age',
            color='Gender',
            nbins=15,
            barmode='overlay',
            color_discrete_sequence=[PRIMARY_COLOR, '#FF6B35']
        )

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Customer Age Distribution by Gender",
                **title_style
            },
            xaxis_title="Age",
            yaxis_title="Number of Customers",
            height=400
        )

        return fig

    def plot_regional_performance_matrix(self):
        regional_metrics = self.filtered_df.groupby('Region').agg({
            'cust_id': 'nunique',
            'revenue': 'sum',
            'order_id': 'nunique'
        }).reset_index()

        regional_metrics['aov'] = regional_metrics['revenue'] / \
            regional_metrics['order_id']

        fig = px.scatter(
            regional_metrics,
            x='cust_id',
            y='aov',
            size='revenue',
            color='Region',
            text='Region',
            color_discrete_sequence=px.colors.sequential.Teal
        )

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Regional Performance: Customers vs AOV",
                **title_style
            },
            xaxis_title="Number of Customers",
            yaxis_title="Average Order Value ($)",
            height=450
        )
        fig.update_traces(textposition='top center')

        return fig

    def plot_category_by_region(self):
        regional_category = self.filtered_df.groupby(['Region', 'category'])[
            'revenue'].sum().reset_index()

        fig = px.bar(
            regional_category,
            x='Region',
            y='revenue',
            color='category',
            barmode='stack',
            color_discrete_sequence=px.colors.sequential.Teal
        )

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Product Category Preferences by Region",
                **title_style
            },
            xaxis_title="Region",
            yaxis_title="Revenue ($)",
            height=500
        )

        return fig

    def plot_order_status_funnel(self):
        # Define funnel stages
        status_counts = self.filtered_df.groupby(
            'status')['order_id'].nunique().reset_index()
        status_counts.columns = ['status', 'count']

        # Order for funnel
        funnel_order = ['received', 'complete',
                        'canceled', 'order_refunded', 'refund', 'cod']
        status_counts['order'] = status_counts['status'].apply(
            lambda x: funnel_order.index(x) if x in funnel_order else 999
        )
        status_counts = status_counts.sort_values('order')

        fig = go.Figure(go.Funnel(
            y=status_counts['status'],
            x=status_counts['count'],
            textinfo="value+percent initial",
            marker={"color": [PRIMARY_COLOR, "#0ea5a5",
                              "#FF6B35", "#EF4444", "#8B5CF6", "#0068C9"]}
        ))

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Order Processing Funnel",
                **title_style
            },
            height=450
        )

        return fig

    def plot_order_status_trend(self):
        status_trend = self.filtered_df.groupby(
            ['order_month_name', 'status', 'order_date']).size().reset_index(name='count')
        status_trend = status_trend.sort_values('order_date')

        fig = px.area(
            status_trend,
            x='order_month_name',
            y='count',
            color='status',
            color_discrete_sequence=px.colors.sequential.Teal
        )

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Order Status Trends Over Time",
                **title_style
            },
            xaxis_title="Month",
            yaxis_title="Number of Orders",
            height=450
        )

        return fig

    def plot_cancellation_analysis(self):
        # Calculate rates by category
        category_status = self.filtered_df.groupby(
            ['category', 'status']).size().reset_index(name='count')
        total_by_category = self.filtered_df.groupby(
            'category').size().reset_index(name='total')

        category_status = category_status.merge(
            total_by_category, on='category')
        category_status['rate'] = (
            category_status['count'] / category_status['total']) * 100

        # Filter for cancelled and refunded
        problem_status = category_status[category_status['status'].isin(
            ['canceled', 'order_refunded'])]

        fig = px.bar(
            problem_status,
            x='category',
            y='rate',
            color='status',
            barmode='group',
            color_discrete_map={
                'canceled': '#EF4444',
                'order_refunded': '#FF6B35'
            }
        )

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Cancellation and Refund Rates by Category",
                **title_style
            },
            xaxis_title="Category",
            yaxis_title="Rate (%)",
            height=450,
            xaxis={'tickangle': 45}
        )

        return fig

    def plot_order_heatmap(self):
        # Create hour and day of week columns if not exist
        df_copy = self.filtered_df.copy()
        df_copy['hour'] = df_copy['order_date'].dt.hour
        df_copy['day_of_week'] = df_copy['order_date'].dt.day_name()

        # Create heatmap data
        heatmap_data = df_copy.groupby(
            ['day_of_week', 'hour']).size().reset_index(name='orders')
        heatmap_pivot = heatmap_data.pivot(
            index='day_of_week', columns='hour', values='orders').fillna(0)

        # Order days
        days_order = ['Monday', 'Tuesday', 'Wednesday',
                      'Thursday', 'Friday', 'Saturday', 'Sunday']
        heatmap_pivot = heatmap_pivot.reindex(days_order)

        fig = go.Figure(data=go.Heatmap(
            z=heatmap_pivot.values,
            x=heatmap_pivot.columns,
            y=heatmap_pivot.index,
            colorscale='Teal',
            text=heatmap_pivot.values,
            texttemplate='%{text}',
            textfont={"size": 10},
            colorbar=dict(title="Orders")
        ))

        title_style = get_title_style()
        fig.update_layout(
            title={
                'text': "Order Volume Heatmap: Day & Time Analysis",
                **title_style
            },
            xaxis_title="Hour of Day",
            yaxis_title="Day of Week",
            height=450
        )

        return fig
