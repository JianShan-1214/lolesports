"""
配置管理模組單元測試
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from config.settings import Settings, ConfigValidationError

class TestSettings:
    """配置管理類別測試"""
    
    def setup_method(self):
        """測試前設定"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
        self.env_file = Path(self.temp_dir) / ".env"
        
        # 儲存原始環境變數
        self.original_env = {}
        test_env_vars = [
            'TELEGRAM_BOT_TOKEN',
            'DATABASE_PATH', 
            'LOGGING_LEVEL',
            'SCHEDULER_MATCH_DATA_FETCH_INTERVAL'
        ]
        
        for var in test_env_vars:
            self.original_env[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
    
    def teardown_method(self):
        """測試後清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # 恢復原始環境變數
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
    
    def test_default_config_creation(self):
        """測試預設配置建立"""
        settings = Settings(str(self.config_file))
        
        # 檢查預設配置是否正確載入
        assert settings.get('telegram.api_url') == 'https://api.telegram.org/bot'
        assert settings.get('leaguepedia.api_url') == 'https://lol.fandom.com/api.php'
        assert settings.get('scheduler.match_data_fetch_interval') == 30
        
        # 檢查配置檔案是否被建立
        assert self.config_file.exists()
    
    def test_config_file_loading(self):
        """測試配置檔案載入"""
        # 建立測試配置檔案
        test_config = {
            "telegram": {
                "bot_token": "test_token_123",
                "api_url": "https://test.api.com"
            },
            "scheduler": {
                "match_data_fetch_interval": 60
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f)
        
        settings = Settings(str(self.config_file))
        
        assert settings.get('telegram.bot_token') == 'test_token_123'
        assert settings.get('telegram.api_url') == 'https://test.api.com'
        assert settings.get('scheduler.match_data_fetch_interval') == 60
    
    def test_environment_variable_override(self):
        """測試環境變數覆蓋配置"""
        # 設定環境變數
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'env_token_456',
            'SCHEDULER_MATCH_DATA_FETCH_INTERVAL': '45'
        }):
            settings = Settings(str(self.config_file))
            
            # 環境變數應該覆蓋配置檔案值
            assert settings.get('telegram.bot_token') == 'env_token_456'
            assert settings.get('scheduler.match_data_fetch_interval') == 45
    
    def test_env_file_loading(self):
        """測試 .env 檔案載入"""
        # 建立 .env 檔案
        env_content = """# 測試環境變數
TELEGRAM_BOT_TOKEN=env_file_token
DATABASE_PATH=test/path.db
LOGGING_LEVEL=DEBUG
"""
        
        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        # 建立 Settings 實例並設定 env_file 路徑
        settings = Settings(str(self.config_file))
        settings.env_file = self.env_file
        settings._load_env_file()
        
        # 檢查環境變數是否正確設定
        assert os.getenv('TELEGRAM_BOT_TOKEN') == 'env_file_token'
        assert os.getenv('DATABASE_PATH') == 'test/path.db'
        assert os.getenv('LOGGING_LEVEL') == 'DEBUG'
    
    def test_config_get_with_default(self):
        """測試取得配置值與預設值"""
        settings = Settings(str(self.config_file))
        
        # 存在的配置
        assert settings.get('telegram.api_url') is not None
        
        # 不存在的配置，使用預設值
        assert settings.get('nonexistent.key', 'default_value') == 'default_value'
        assert settings.get('nonexistent.key') is None
    
    def test_config_set_and_save(self):
        """測試設定和儲存配置"""
        settings = Settings(str(self.config_file))
        
        # 設定新值
        settings.set('telegram.bot_token', 'new_token_789')
        settings.set('custom.new_key', 'new_value')
        
        # 檢查值是否正確設定
        assert settings.get('telegram.bot_token') == 'new_token_789'
        assert settings.get('custom.new_key') == 'new_value'
        
        # 重新載入配置檢查是否持久化
        new_settings = Settings(str(self.config_file))
        assert new_settings.get('telegram.bot_token') == 'new_token_789'
        assert new_settings.get('custom.new_key') == 'new_value'
    
    def test_config_validation(self):
        """測試配置驗證"""
        settings = Settings(str(self.config_file))
        
        # 測試空的必要配置
        errors = settings.validate_configuration()
        assert len(errors) > 0
        assert any('telegram.bot_token' in error for error in errors)
        
        # 設定必要配置
        settings.set('telegram.bot_token', 'valid_token')
        
        # 測試無效的數值範圍
        settings.set('scheduler.match_data_fetch_interval', 0)  # 無效值
        errors = settings.validate_configuration()
        assert any('match_data_fetch_interval' in error for error in errors)
        
        # 設定有效值
        settings.set('scheduler.match_data_fetch_interval', 30)
        errors = settings.validate_configuration()
        # 應該減少錯誤數量
        assert len([e for e in errors if 'match_data_fetch_interval' in e]) == 0
    
    def test_convert_env_value(self):
        """測試環境變數值轉換"""
        settings = Settings(str(self.config_file))
        
        # 測試布林值轉換
        assert settings._convert_env_value('true') is True
        assert settings._convert_env_value('false') is False
        assert settings._convert_env_value('True') is True
        assert settings._convert_env_value('FALSE') is False
        
        # 測試整數轉換
        assert settings._convert_env_value('123') == 123
        assert settings._convert_env_value('-456') == -456
        
        # 測試浮點數轉換
        assert settings._convert_env_value('12.34') == 12.34
        assert settings._convert_env_value('-56.78') == -56.78
        
        # 測試字串
        assert settings._convert_env_value('hello') == 'hello'
        assert settings._convert_env_value('') == ''
    
    def test_properties(self):
        """測試便利屬性方法"""
        settings = Settings(str(self.config_file))
        
        # 設定一些測試值
        settings.set('telegram.bot_token', 'test_token')
        settings.set('database.path', 'test/db.sqlite')
        settings.set('logging.level', 'DEBUG')
        
        # 測試屬性
        assert settings.telegram_bot_token == 'test_token'
        assert settings.database_path == 'test/db.sqlite'
        assert settings.log_level == 'DEBUG'
        assert settings.telegram_api_url == 'https://api.telegram.org/bot'
    
    def test_get_all_config_with_sensitive_data_hidden(self):
        """測試取得所有配置時隱藏敏感資訊"""
        settings = Settings(str(self.config_file))
        
        # 設定敏感資訊
        long_token = 'very_long_secret_token_12345678'
        settings.set('telegram.bot_token', long_token)
        
        all_config = settings.get_all_config()
        
        # 檢查敏感資訊是否被隱藏
        assert all_config['telegram']['bot_token'] != long_token
        assert '...' in all_config['telegram']['bot_token']
        assert all_config['telegram']['bot_token'].startswith('very_long_')
        assert all_config['telegram']['bot_token'].endswith('5678')
    
    def test_invalid_json_config_file(self):
        """測試無效的JSON配置檔案"""
        # 建立無效的JSON檔案
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.write('{ invalid json content }')
        
        # 應該拋出配置驗證錯誤
        with pytest.raises(ConfigValidationError):
            Settings(str(self.config_file))
    
    def test_create_env_template(self):
        """測試建立環境變數範本"""
        settings = Settings(str(self.config_file))
        
        # 修改範本路徑到測試目錄
        template_path = Path(self.temp_dir) / ".env.template"
        
        with patch('config.settings.Path') as mock_path:
            mock_path.return_value = template_path
            settings.create_env_template()
        
        # 檢查範本檔案是否建立
        assert template_path.exists()
        
        # 檢查範本內容
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'TELEGRAM_BOT_TOKEN' in content
            assert 'DATABASE_PATH' in content
            assert 'LOGGING_LEVEL' in content
    
    def test_reload_config(self):
        """測試重新載入配置"""
        settings = Settings(str(self.config_file))
        
        # 取得初始值
        initial_token = settings.get('telegram.bot_token')
        
        # 直接修改配置檔案
        new_config = settings._config.copy()
        new_config['telegram']['bot_token'] = 'reloaded_token'
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(new_config, f)
        
        # 重新載入配置
        settings.reload_config()
        
        # 檢查配置是否更新
        assert settings.get('telegram.bot_token') == 'reloaded_token'