"""Add Row Level Security

Revision ID: af23c5db8e9f
Revises: c42c5fae8bfb
Create Date: 2025-04-23 19:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'af23c5db8e9f'
down_revision: Union[str, None] = 'c42c5fae8bfb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with Row Level Security"""
    # Enable Row Level Security on the main tables
    op.execute("ALTER TABLE public.true_prices ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.market_snapshots ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.trader_scores ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.alert_rules ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.alert_notifications ENABLE ROW LEVEL SECURITY;")
    
    # Create RLS Policies for public read access (needed for frontend to access data)
    # True Prices - Read-only for all users
    op.execute("""
    CREATE POLICY "Allow public read access for true_prices" 
    ON public.true_prices FOR SELECT 
    USING (true);
    """)
    
    # Market Snapshots - Read-only for all users
    op.execute("""
    CREATE POLICY "Allow public read access for market_snapshots" 
    ON public.market_snapshots FOR SELECT 
    USING (true);
    """)
    
    # Markets - Read-only for all users
    op.execute("""
    CREATE POLICY "Allow public read access for markets" 
    ON public.markets FOR SELECT 
    USING (true);
    """)
    
    # Trader Scores - Read-only for all users (for leaderboard)
    op.execute("""
    CREATE POLICY "Allow public read access for trader_scores" 
    ON public.trader_scores FOR SELECT 
    USING (true);
    """)
    
    # Traders - Read-only for all users
    op.execute("""
    CREATE POLICY "Allow public read access for traders" 
    ON public.traders FOR SELECT 
    USING (true);
    """)
    
    # Alert Rules - authenticated users only
    op.execute("""
    CREATE POLICY "Allow authenticated read access for alert_rules" 
    ON public.alert_rules FOR SELECT 
    USING (auth.role() = 'authenticated');
    """)
    
    # Alert Notifications - authenticated users only
    op.execute("""
    CREATE POLICY "Allow authenticated read access for alert_notifications" 
    ON public.alert_notifications FOR SELECT 
    USING (auth.role() = 'authenticated');
    """)
    
    # Create or modify the Supabase Realtime publication
    # First check if publication exists
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
            -- Create the publication if it doesn't exist
            EXECUTE 'CREATE PUBLICATION supabase_realtime FOR TABLE true_prices, market_snapshots, trader_scores';
        ELSE
            -- Add tables to the existing publication if they aren't already included
            -- This is a simplified approach - in production you might want to check if tables are already in the publication
            EXECUTE 'ALTER PUBLICATION supabase_realtime ADD TABLE true_prices, market_snapshots, trader_scores';
        END IF;
    END
    $$;
    """)


def downgrade() -> None:
    """Downgrade schema - remove RLS"""
    # Remove policies
    op.execute("DROP POLICY IF EXISTS \"Allow public read access for true_prices\" ON public.true_prices;")
    op.execute("DROP POLICY IF EXISTS \"Allow public read access for market_snapshots\" ON public.market_snapshots;")
    op.execute("DROP POLICY IF EXISTS \"Allow public read access for markets\" ON public.markets;")
    op.execute("DROP POLICY IF EXISTS \"Allow public read access for trader_scores\" ON public.trader_scores;")
    op.execute("DROP POLICY IF EXISTS \"Allow public read access for traders\" ON public.traders;")
    op.execute("DROP POLICY IF EXISTS \"Allow authenticated read access for alert_rules\" ON public.alert_rules;")
    op.execute("DROP POLICY IF EXISTS \"Allow authenticated read access for alert_notifications\" ON public.alert_notifications;")
    
    # Disable RLS
    op.execute("ALTER TABLE IF EXISTS public.true_prices DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE IF EXISTS public.market_snapshots DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE IF EXISTS public.trader_scores DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE IF EXISTS public.alert_rules DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE IF EXISTS public.alert_notifications DISABLE ROW LEVEL SECURITY;")
    
    # Note: We don't remove tables from the publication as it might be used by other features