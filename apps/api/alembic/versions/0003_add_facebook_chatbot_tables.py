"""Facebook Chatbot System - Database Schema

Alembic migration to add Facebook conversation tracking and chatbot tables.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Index


def upgrade():
    """Create chatbot-related tables for Facebook integration."""
    
    # 1. Facebook Conversation Threads
    op.create_table(
        'fb_conversation_thread',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('psid', sa.Text(), nullable=False),
        sa.Column('customer_name', sa.Text(), nullable=True),
        sa.Column('topic_inferred', sa.Text(), nullable=True),
        sa.Column('last_message_at', sa.DateTime(), nullable=True),
        sa.Column('message_count', sa.Integer(), default=0),
        sa.Column('status', sa.Text(), default='open'),
        sa.Column('assigned_to_nv_id', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['assigned_to_nv_id'], ['users.nv_id'])
    )
    op.create_index('ix_fb_conversation_thread_psid', 'fb_conversation_thread', ['psid'])
    op.create_index('ix_fb_conversation_thread_status', 'fb_conversation_thread', ['status'])
    
    # 2. Facebook Message Log
    op.create_table(
        'fb_message_log',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('thread_id', sa.Text(), nullable=False),
        sa.Column('sender_id', sa.Text(), nullable=False),
        sa.Column('sender_type', sa.Text(), nullable=True),  # "customer" or "agent"
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('reply_to_id', sa.Text(), nullable=True),
        sa.Column('sentiment', sa.Text(), nullable=True),  # "positive", "neutral", "negative"
        sa.Column('intent_classified', sa.Text(), nullable=True),
        sa.Column('intent_confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['thread_id'], ['fb_conversation_thread.id'])
    )
    op.create_index('ix_fb_message_log_thread_id', 'fb_message_log', ['thread_id'])
    op.create_index('ix_fb_message_log_intent', 'fb_message_log', ['intent_classified'])
    
    # 3. Chatbot Intent Definitions
    op.create_table(
        'chatbot_intent',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('display_name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sample_questions', sa.Text(), nullable=True),  # JSON
        sa.Column('requires_approval', sa.Integer(), default=0),
        sa.Column('auto_response_enabled', sa.Integer(), default=1),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id')
    )
    
    # 4. Chatbot Response Rules
    op.create_table(
        'chatbot_response_rule',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('intent', sa.Text(), nullable=False),
        sa.Column('condition', sa.Text(), nullable=True),  # JSON optional conditions
        sa.Column('response_template', sa.Text(), nullable=False),
        sa.Column('confidence_threshold', sa.Float(), default=0.8),
        sa.Column('enabled', sa.Integer(), default=1),
        sa.Column('created_by_nv_id', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by_nv_id'], ['users.nv_id']),
        sa.ForeignKeyConstraint(['intent'], ['chatbot_intent.id'])
    )
    op.create_index('ix_chatbot_response_rule_intent', 'chatbot_response_rule', ['intent'])
    op.create_index('ix_chatbot_response_rule_enabled', 'chatbot_response_rule', ['enabled'])
    
    # 5. Chatbot Knowledge Base
    op.create_table(
        'chatbot_kb',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('category', sa.Text(), nullable=False),
        sa.Column('key_phrase', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sources', sa.Text(), nullable=True),  # JSON array
        sa.Column('confidence', sa.Float(), default=1.0),
        sa.Column('dynamic_from_table', sa.Text(), nullable=True),  # e.g., "menu_mon"
        sa.Column('last_updated', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chatbot_kb_category', 'chatbot_kb', ['category'])
    
    # 6. Chatbot Analytics
    op.create_table(
        'chatbot_analytics',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('thread_id', sa.Text(), nullable=True),
        sa.Column('intent_classified', sa.Text(), nullable=True),
        sa.Column('intent_confidence', sa.Float(), nullable=True),
        sa.Column('was_auto_responded', sa.Integer(), nullable=True),  # 1=yes, 0=no
        sa.Column('human_response_time_seconds', sa.Integer(), nullable=True),
        sa.Column('customer_satisfied', sa.Integer(), nullable=True),  # 1=yes, 0=no, NULL=unknown
        sa.Column('feedback_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['thread_id'], ['fb_conversation_thread.id'])
    )
    op.create_index('ix_chatbot_analytics_intent', 'chatbot_analytics', ['intent_classified'])
    op.create_index('ix_chatbot_analytics_created_at', 'chatbot_analytics', ['created_at'])


def downgrade():
    """Drop all chatbot-related tables."""
    op.drop_index('ix_chatbot_analytics_created_at', 'chatbot_analytics')
    op.drop_index('ix_chatbot_analytics_intent', 'chatbot_analytics')
    op.drop_table('chatbot_analytics')
    
    op.drop_index('ix_chatbot_kb_category', 'chatbot_kb')
    op.drop_table('chatbot_kb')
    
    op.drop_index('ix_chatbot_response_rule_enabled', 'chatbot_response_rule')
    op.drop_index('ix_chatbot_response_rule_intent', 'chatbot_response_rule')
    op.drop_table('chatbot_response_rule')
    
    op.drop_table('chatbot_intent')
    
    op.drop_index('ix_fb_message_log_intent', 'fb_message_log')
    op.drop_index('ix_fb_message_log_thread_id', 'fb_message_log')
    op.drop_table('fb_message_log')
    
    op.drop_index('ix_fb_conversation_thread_status', 'fb_conversation_thread')
    op.drop_index('ix_fb_conversation_thread_psid', 'fb_conversation_thread')
    op.drop_table('fb_conversation_thread')
