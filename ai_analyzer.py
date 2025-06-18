import os
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """AI-powered performance issue analyzer"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.model = "gpt-4o"
    
    def analyze_file_for_issues(self, filename, content, file_type="unknown"):
        """
        Analyze a single file for performance issues
        Returns dict with potential issues found
        """
        try:
            prompt = self._create_analysis_prompt(filename, content, file_type)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Вы эксперт по тестированию производительности. Анализируйте код на предмет проблем производительности и потенциальных узких мест. Отвечайте на русском языке в формате JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"AI анализ завершен для файла {filename}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка AI анализа файла {filename}: {str(e)}")
            return {
                "issues": [],
                "error": f"Ошибка анализа: {str(e)}"
            }
    
    def _create_analysis_prompt(self, filename, content, file_type):
        """Create analysis prompt for the AI"""
        return f"""
Проанализируйте следующий файл на предмет проблем производительности в контексте нагрузочного тестирования:

Имя файла: {filename}
Тип файла: {file_type}

Код:
