import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

# Load the dataset
df = pd.read_excel("data/E-commerce Customer Behavior.xlsx")
# Preprocessing (mirroring Colab)
df['Satisfaction Level'].fillna('Unknown', inplace=True)
df['Age Group'] = pd.cut(df['Age'], bins=[20, 30, 40, 50], labels=['20-30', '31-40', '41-50'], include_lowest=True)
df['Spend per Item'] = df['Total Spend'] / df['Items Purchased']
df['Churn Risk'] = df['Days Since Last Purchase'] > 30
df['High Value Customer'] = df['Total Spend'] > df['Total Spend'].quantile(0.75)
df['Frequent Buyer'] = df['Items Purchased'] > df['Items Purchased'].median()
df['Recent Buyer'] = df['Days Since Last Purchase'] < 15

# Clustering
features = df[['Total Spend', 'Items Purchased', 'Average Rating', 'Spend per Item']]
scaler = StandardScaler()
scaled = scaler.fit_transform(features)
kmeans = KMeans(n_clusters=3, random_state=42)
df['Cluster'] = kmeans.fit_predict(scaled)

# PCA for visualization
pca = PCA(n_components=2)
reduced_features = pca.fit_transform(scaled)
df['PCA1'] = reduced_features[:, 0]
df['PCA2'] = reduced_features[:, 1]

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# Main layout with navigation
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Nav([
        dcc.Link('Dashboard', href='/', className='nav-link'),
        dcc.Link('Data Exploration', href='/data-exploration', className='nav-link'),
        dcc.Link('Customer Segmentation', href='/segmentation', className='nav-link'),
        dcc.Link('Churn Analysis', href='/churn', className='nav-link'),
        dcc.Link('Recommendations', href='/recommendations', className='nav-link'),
    ], className='navbar'),
    html.Div(id='page-content', className='content')
])

# Callback to render pages
@app.callback(Output('page-content', 'children'), [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/data-exploration':
        return data_exploration_layout
    elif pathname == '/segmentation':
        return segmentation_layout
    elif pathname == '/churn':
        return churn_layout
    elif pathname == '/recommendations':
        return recommendations_layout
    else:
        return dashboard_layout

# Dashboard layout
dashboard_layout = html.Div([
    html.H1('E-commerce Customer Behavior Dashboard'),
    html.P('An overview of key metrics and trends.'),
    html.Div([
        html.Div([
            html.H3('Total Customers'),
            html.P(str(len(df)))
        ], className='card'),
        html.Div([
            html.H3('Average Total Spend'),
            html.P(f"${df['Total Spend'].mean():.2f}")
        ], className='card'),
        html.Div([
            html.H3('Average Items Purchased'),
            html.P(f"{df['Items Purchased'].mean():.2f}")
        ], className='card'),
    ], className='row'),
    dcc.Graph(figure=px.histogram(df, x='Total Spend', title='Distribution of Total Spend', nbins=30)),
    dcc.Graph(figure=px.pie(df, names='Membership Type', title='Membership Type Distribution')),
])

# Data Exploration layout
numerical_cols = df.select_dtypes(include=[np.number]).columns
data_exploration_layout = html.Div([
    html.H1('Data Exploration'),
    html.P('Explore the dataset with interactive tools.'),
    dash_table.DataTable(
        id='table',
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
        page_size=10,
        style_table={'overflowX': 'auto'},
    ),
    dcc.Dropdown(
        id='feature-dropdown',
        options=[{'label': col, 'value': col} for col in numerical_cols],
        value='Total Spend',
        className='dropdown'
    ),
    dcc.Graph(id='feature-histogram'),
])

# Customer Segmentation layout
segmentation_layout = html.Div([
    html.H1('Customer Segmentation'),
    html.P('View customer clusters based on spending behavior.'),
    dcc.Graph(
        id='cluster-scatter',
        figure=px.scatter(df, x='PCA1', y='PCA2', color='Cluster', title='Customer Clusters (PCA)',
                          hover_data=['Total Spend', 'Items Purchased'])
    ),
    html.H2('Cluster Statistics'),
    html.Table([
        html.Tr([html.Th('Cluster'), html.Th('Avg Total Spend'), html.Th('Avg Items Purchased')]),
        *[html.Tr([html.Td(i), html.Td(f"${df[df['Cluster']==i]['Total Spend'].mean():.2f}"),
                   html.Td(f"{df[df['Cluster']==i]['Items Purchased'].mean():.2f}")])
          for i in range(3)]
    ], className='table'),
])

# Churn Analysis layout
churn_layout = html.Div([
    html.H1('Churn Analysis'),
    html.P('Analyze churn risk across membership types.'),
    dcc.Dropdown(
        id='membership-dropdown',
        options=[{'label': m, 'value': m} for m in df['Membership Type'].unique()],
        multi=True,
        value=list(df['Membership Type'].unique()),
        className='dropdown'
    ),
    dcc.Graph(id='churn-count-plot'),
])

# Recommendations layout
recommendations_layout = html.Div([
    html.H1('Business Recommendations'),
    html.P('Actionable insights based on the analysis.'),
    html.Ul([
        html.Li("Provide loyalty benefits or exclusive offers to high-value customers to enhance retention."),
        html.Li("Identify and re-engage customers at risk of churning (no purchase in 30+ days) with email or SMS campaigns."),
        html.Li("Focus marketing strategies on the 31–40 age group showing higher mid-to-high spend behavior."),
        html.Li("Consider bundling frequently bought items to increase 'Spend per Item' for low-value segments."),
        html.Li("Leverage customer clusters for personalized promotions and product recommendations."),
        html.Li("Monitor recent buyers to send automated feedback or thank-you messages to maintain engagement."),
    ]),
])

# Callbacks for interactivity
@app.callback(
    Output('feature-histogram', 'figure'),
    [Input('feature-dropdown', 'value')]
)
def update_histogram(selected_feature):
    fig = px.histogram(df, x=selected_feature, title=f'Distribution of {selected_feature}', nbins=30)
    fig.update_layout(xaxis_title=selected_feature, yaxis_title='Count')
    return fig

@app.callback(
    Output('churn-count-plot', 'figure'),
    [Input('membership-dropdown', 'value')]
)
def update_churn_plot(selected_memberships):
    filtered_df = df[df['Membership Type'].isin(selected_memberships)]
    fig = px.histogram(filtered_df, x='Membership Type', color='Churn Risk', barmode='group',
                       title='Churn Risk by Membership Type')
    fig.update_layout(xaxis_title='Membership Type', yaxis_title='Count')
    return fig

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
