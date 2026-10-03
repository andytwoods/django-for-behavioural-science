// Minimal Stroop task: respond to the INK colour (r = red, g = green, b = blue).
// This is a jsPsych timeline. Paste it into a new study's "code" field in the admin.
// (The finished app also loads it for you, in a seed migration.)
const fixation = {
  type: jsPsychHtmlKeyboardResponse,
  stimulus: '<p style="font-size:48px;">+</p>',
  choices: "NO_KEYS",
  trial_duration: 500
};

const stroop = {
  type: jsPsychHtmlKeyboardResponse,
  stimulus: jsPsych.timelineVariable('stimulus'),
  choices: ['r', 'g', 'b'],
  data: {
    congruency: jsPsych.timelineVariable('congruency'),
    correct_response: jsPsych.timelineVariable('correct_response')
  },
  on_finish: function (data) {
    data.correct = jsPsych.pluginAPI.compareKeys(data.response, data.correct_response);
  }
};

const instructions = {
  type: jsPsychHtmlKeyboardResponse,
  stimulus: '<p>Respond to the INK colour: <b>r</b> = red, <b>g</b> = green, <b>b</b> = blue.</p>' +
            '<p>Press any key to begin.</p>'
};

timeline.push(instructions);
timeline.push({
  timeline: [fixation, stroop],
  timeline_variables: [
    { stimulus: '<span style="color:red;font-size:48px;">RED</span>',     congruency: 'congruent',  correct_response: 'r' },
    { stimulus: '<span style="color:green;font-size:48px;">GREEN</span>', congruency: 'congruent',  correct_response: 'g' },
    { stimulus: '<span style="color:blue;font-size:48px;">RED</span>',    congruency: 'incongruent', correct_response: 'b' },
    { stimulus: '<span style="color:red;font-size:48px;">GREEN</span>',   congruency: 'incongruent', correct_response: 'r' }
  ],
  randomize_order: true,
  repetitions: 2
});
