#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#define LCD_SDA 21
#define LCD_SCL 22

LiquidCrystal_I2C lcd(0x27, 16, 2);

void setup() {

  Wire.begin(LCD_SDA, LCD_SCL);

  lcd.init();
  lcd.backlight();

  lcd.clear();

  lcd.setCursor(0, 0);
  lcd.print("THE GLOBAL DERA");

  lcd.setCursor(0, 1);
  lcd.print("THE CLOUD IS AWS");
}

void loop() {
}